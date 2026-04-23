from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import AnalysisResult, NotificationLog, PriceBar, Symbol


def _business_days(start_date: date, end_date: date) -> list[date]:
    days: list[date] = []
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def _ensure_symbol(db: Session, ticker: str) -> bool:
    existing = db.scalar(select(Symbol).where(Symbol.ticker == ticker))
    if existing:
        if existing.is_active == 0:
            existing.is_active = 1
        if existing.market != "TEST":
            existing.market = "TEST"
        return False
    db.add(Symbol(ticker=ticker, market="TEST", is_active=1))
    return True


def generate_test_price_bars(
    db: Session,
    ticker: str,
    start_date: date,
    end_date: date,
    *,
    start_price: float = 1000.0,
    drift: float = 0.0002,
    volatility: float = 0.02,
    seed: int | None = None,
) -> dict[str, int | str]:
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")
    if start_price <= 0:
        raise ValueError("start_price must be greater than 0")
    if volatility <= 0:
        raise ValueError("volatility must be greater than 0")

    created_symbol = _ensure_symbol(db, ticker)
    rng = random.Random(seed)
    bar_dates = _business_days(start_date, end_date)
    now = datetime.now(timezone.utc)

    inserted_or_updated = 0
    prev_close = start_price

    for bar_date in bar_dates:
        daily_return = drift + rng.gauss(0, volatility)
        close = max(1.0, prev_close * (1 + daily_return))
        open_price = max(1.0, prev_close * (1 + rng.gauss(0, volatility * 0.5)))

        high_base = max(open_price, close)
        low_base = min(open_price, close)
        high = high_base * (1 + abs(rng.gauss(0, volatility * 0.4)))
        low = max(1.0, low_base * (1 - abs(rng.gauss(0, volatility * 0.4))))
        volume = float(max(1000, int(rng.lognormvariate(13.0, 0.35))))

        existing = db.scalar(
            select(PriceBar).where(
                PriceBar.ticker == ticker,
                PriceBar.bar_date == bar_date,
                PriceBar.interval == "1d",
                PriceBar.source == "synthetic",
            )
        )

        payload = {
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "adjusted_close": close,
            "fetched_at": now,
        }
        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
        else:
            db.add(
                PriceBar(
                    ticker=ticker,
                    bar_date=bar_date,
                    interval="1d",
                    source="synthetic",
                    **payload,
                )
            )
        inserted_or_updated += 1
        prev_close = close

    db.commit()

    return {
        "ticker": ticker,
        "symbol_created": 1 if created_symbol else 0,
        "bars_upserted": inserted_or_updated,
        "business_days": len(bar_dates),
    }


def delete_test_ticker_data(db: Session, ticker: str) -> dict[str, int | str]:
    bars_deleted = db.execute(
        delete(PriceBar).where(PriceBar.ticker == ticker, PriceBar.source == "synthetic")
    ).rowcount or 0
    analysis_deleted = db.execute(delete(AnalysisResult).where(AnalysisResult.ticker == ticker)).rowcount or 0
    notifications_deleted = (
        db.execute(delete(NotificationLog).where(NotificationLog.ticker == ticker)).rowcount or 0
    )
    symbols_deleted = db.execute(delete(Symbol).where(Symbol.ticker == ticker, Symbol.market == "TEST")).rowcount or 0
    db.commit()

    return {
        "ticker": ticker,
        "bars_deleted": bars_deleted,
        "analysis_deleted": analysis_deleted,
        "notifications_deleted": notifications_deleted,
        "symbols_deleted": symbols_deleted,
    }
