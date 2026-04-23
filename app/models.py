from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Symbol(Base):
    __tablename__ = "symbols"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    market: Mapped[str] = mapped_column(String(16), default="UNKNOWN")
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32), index=True)
    run_type: Mapped[str] = mapped_column(String(16), default="weekly")
    timeframe: Mapped[str] = mapped_column(String(16), default="daily")
    trend_score: Mapped[int] = mapped_column(Integer)
    dip_score: Mapped[int] = mapped_column(Integer)
    breakout_score: Mapped[int] = mapped_column(Integer)
    total_score: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="watch")
    reasons: Mapped[str] = mapped_column(Text)
    as_of_date: Mapped[date] = mapped_column(Date, index=True)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class NotificationLog(Base):
    __tablename__ = "notification_logs"
    __table_args__ = (
        UniqueConstraint("ticker", "timeframe", "notified_period_key", name="uq_notif_period"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32), index=True)
    timeframe: Mapped[str] = mapped_column(String(16), index=True)
    notified_period_key: Mapped[str] = mapped_column(String(32), index=True)
    channel: Mapped[str] = mapped_column(String(16), default="discord")
    message: Mapped[str] = mapped_column(Text)
    notified_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class PriceBar(Base):
    __tablename__ = "price_bars"
    __table_args__ = (
        UniqueConstraint("ticker", "bar_date", "interval", "source", name="uq_price_bar"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32), index=True)
    bar_date: Mapped[date] = mapped_column(Date, index=True)
    interval: Mapped[str] = mapped_column(String(8), default="1d", index=True)
    source: Mapped[str] = mapped_column(String(32), default="yahoo", index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    adjusted_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
