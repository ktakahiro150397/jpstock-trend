from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.data_sources.yahoo import YahooFinanceDataSource
from app.models import PriceBar, Symbol


def ensure_symbols(db: Session) -> None:
    settings = get_settings()
    for ticker in settings.symbols:
        exists = db.scalar(select(Symbol).where(Symbol.ticker == ticker))
        if exists:
            continue
        market = "JP" if ticker.endswith(".T") else "US"
        db.add(Symbol(ticker=ticker, market=market))
    db.commit()


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = df.copy()
    # yfinance may return MultiIndex columns on some versions
    if isinstance(renamed.columns, pd.MultiIndex):
        renamed.columns = [c[0] for c in renamed.columns]
    if "Adj Close" in renamed.columns and "AdjustedClose" not in renamed.columns:
        renamed = renamed.rename(columns={"Adj Close": "AdjustedClose"})
    for c in ["Open", "High", "Low", "Close", "Volume"]:
        if c not in renamed.columns:
            renamed[c] = 0.0
    if "AdjustedClose" not in renamed.columns:
        renamed["AdjustedClose"] = None
    return renamed[["Open", "High", "Low", "Close", "Volume", "AdjustedClose"]]


def _upsert_price_bars(db: Session, ticker: str, interval: str, source: str, frame: pd.DataFrame) -> int:
    inserted_or_updated = 0
    for idx, row in frame.iterrows():
        bar_date = idx.date()
        stmt = select(PriceBar).where(
            PriceBar.ticker == ticker,
            PriceBar.bar_date == bar_date,
            PriceBar.interval == interval,
            PriceBar.source == source,
        )
        existing = db.scalar(stmt)
        payload = {
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": float(row["Volume"]),
            "adjusted_close": (None if pd.isna(row["AdjustedClose"]) else float(row["AdjustedClose"])),
            "fetched_at": datetime.now(timezone.utc),
        }
        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
        else:
            db.add(
                PriceBar(
                    ticker=ticker,
                    bar_date=bar_date,
                    interval=interval,
                    source=source,
                    **payload,
                )
            )
        inserted_or_updated += 1
    return inserted_or_updated


def ingest_market_data(db: Session, as_of_date: date | None = None) -> dict[str, int]:
    settings = get_settings()
    ensure_symbols(db)
    datasource = YahooFinanceDataSource()

    target = as_of_date or datetime.now(timezone.utc).date()
    # 1年超の分析・再計算を考慮して余裕を持って取り込む
    lookback_days = max(settings.analysis_lookback_days, 800)

    symbols = db.scalars(select(Symbol).where(Symbol.is_active == 1)).all()
    total = 0

    for symbol in symbols:
        raw = datasource.fetch_ohlcv(symbol.ticker, lookback_days=lookback_days, as_of_date=target)
        if raw.empty:
            continue
        normalized = _normalize_columns(raw)
        total += _upsert_price_bars(db, ticker=symbol.ticker, interval="1d", source="yahoo", frame=normalized)

    db.commit()
    return {"symbols": len(symbols), "bars_upserted": total}


def load_daily_bars_from_db(db: Session, ticker: str, as_of_date: date, lookback_days: int) -> pd.DataFrame:
    start_date = as_of_date - timedelta(days=lookback_days)
    rows = db.scalars(
        select(PriceBar)
        .where(
            PriceBar.ticker == ticker,
            PriceBar.interval == "1d",
            PriceBar.bar_date >= start_date,
            PriceBar.bar_date <= as_of_date,
        )
        .order_by(PriceBar.bar_date.asc())
    ).all()

    if not rows:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    frame = pd.DataFrame(
        {
            "Open": [r.open for r in rows],
            "High": [r.high for r in rows],
            "Low": [r.low for r in rows],
            "Close": [r.close for r in rows],
            "Volume": [r.volume for r in rows],
        },
        index=pd.to_datetime([r.bar_date for r in rows]),
    )
    frame.index.name = "Date"
    return frame
