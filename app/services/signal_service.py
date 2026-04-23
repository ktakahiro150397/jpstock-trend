from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis import SignalResult, analyze_symbol
from app.config import get_settings
from app.models import AnalysisResult, NotificationLog, Symbol
from app.services.ingest_service import load_daily_bars_from_db
from app.services.notify import build_discord_message, send_discord


def timeframe_period_key(now: datetime, timeframe: str) -> str:
    if timeframe == "daily":
        return (now.date()).isoformat()
    if timeframe == "weekly":
        year, week, _ = now.isocalendar()
        return f"{year}-W{week:02d}"
    return f"{now.year}-{now.month:02d}"


def _cooldown_keys(now: datetime, timeframe: str) -> set[str]:
    # MVP: 現在を含む直近2単位を抑制
    if timeframe == "daily":
        return {(now.date()).isoformat(), (now.date().fromordinal(now.date().toordinal() - 1)).isoformat()}
    if timeframe == "weekly":
        y1, w1, _ = now.isocalendar()
        prev = now.fromordinal(now.toordinal() - 7)
        y2, w2, _ = prev.isocalendar()
        return {f"{y1}-W{w1:02d}", f"{y2}-W{w2:02d}"}
    prev_month = now.month - 1 if now.month > 1 else 12
    prev_year = now.year if now.month > 1 else now.year - 1
    return {f"{now.year}-{now.month:02d}", f"{prev_year}-{prev_month:02d}"}


def _should_notify(db: Session, ticker: str, timeframe: str, now: datetime) -> bool:
    keys = _cooldown_keys(now, timeframe)
    stmt = select(NotificationLog).where(
        NotificationLog.ticker == ticker,
        NotificationLog.timeframe == timeframe,
        NotificationLog.notified_period_key.in_(keys),
    )
    return db.scalar(stmt) is None


def ensure_symbols(db: Session) -> None:
    settings = get_settings()
    for ticker in settings.symbols:
        exists = db.scalar(select(Symbol).where(Symbol.ticker == ticker))
        if exists:
            continue
        market = "JP" if ticker.endswith(".T") else "US"
        db.add(Symbol(ticker=ticker, market=market))
    db.commit()


def run_analysis(db: Session, run_type: str = "weekly", as_of_date: date | None = None) -> list[SignalResult]:
    settings = get_settings()

    ensure_symbols(db)

    symbols = db.scalars(select(Symbol).where(Symbol.is_active == 1)).all()
    now = datetime.now(timezone.utc)
    target_date = as_of_date or now.date()

    results: list[SignalResult] = []

    for symbol in symbols:
        df = load_daily_bars_from_db(db, symbol.ticker, as_of_date=target_date, lookback_days=settings.analysis_lookback_days)
        result = analyze_symbol(symbol.ticker, df, settings.notify_threshold)
        results.append(result)

        db.add(
            AnalysisResult(
                ticker=result.ticker,
                run_type=run_type,
                timeframe="daily",
                trend_score=result.trend_score,
                dip_score=result.dip_score,
                breakout_score=result.breakout_score,
                total_score=result.total_score,
                status=result.status,
                reasons="\n".join(result.reasons),
                as_of_date=target_date,
                analyzed_at=now,
            )
        )

    db.commit()

    should_send_notifications = run_type == "weekly" and as_of_date is None
    candidates = [r for r in results if r.status == "entry_candidate" and _should_notify(db, r.ticker, "weekly", now)]
    if candidates and should_send_notifications:
        message = build_discord_message(candidates)
        send_discord(settings.discord_webhook_url, message)
        key = timeframe_period_key(now, "weekly")
        for row in candidates:
            db.add(
                NotificationLog(
                    ticker=row.ticker,
                    timeframe="weekly",
                    notified_period_key=key,
                    message=message,
                )
            )
        db.commit()

    return results
