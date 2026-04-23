from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base
from app.models import AnalysisResult, NotificationLog, PriceBar, Symbol
from app.services.test_data_service import delete_test_ticker_data, generate_test_price_bars


def _make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    local_session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return local_session()


def test_generate_creates_test_symbol_and_synthetic_bars() -> None:
    with _make_session() as db:
        result = generate_test_price_bars(
            db,
            ticker="ZZZTEST.T",
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 3),
            seed=42,
        )

        symbol = db.scalar(select(Symbol).where(Symbol.ticker == "ZZZTEST.T"))
        bars = db.scalars(select(PriceBar).where(PriceBar.ticker == "ZZZTEST.T", PriceBar.source == "synthetic")).all()

        assert result["symbol_created"] == 1
        assert result["bars_upserted"] == 3
        assert symbol is not None
        assert symbol.market == "TEST"
        assert len(bars) == 3


def test_generate_rejects_existing_non_test_symbol() -> None:
    with _make_session() as db:
        db.add(Symbol(ticker="ZZZLIVE.T", market="TSE", is_active=1))
        db.commit()

        try:
            generate_test_price_bars(
                db,
                ticker="ZZZLIVE.T",
                start_date=date(2026, 4, 1),
                end_date=date(2026, 4, 2),
            )
            assert False, "expected ValueError for existing non-TEST ticker"
        except ValueError as exc:
            assert "non-TEST symbol" in str(exc)


def test_delete_non_test_ticker_does_not_delete_analysis_or_notifications() -> None:
    with _make_session() as db:
        db.add(Symbol(ticker="ZZZLIVE.T", market="TSE", is_active=1))
        db.add(
            AnalysisResult(
                ticker="ZZZLIVE.T",
                as_of_date=date(2026, 4, 1),
                trend_score=1,
                dip_score=1,
                breakout_score=1,
                total_score=3,
                reasons="seed",
            )
        )
        db.add(
            NotificationLog(
                ticker="ZZZLIVE.T",
                timeframe="daily",
                notified_period_key="2026-04-01",
                message="seed",
            )
        )
        db.commit()

        result = delete_test_ticker_data(db, ticker="ZZZLIVE.T")
        analysis_rows = db.scalars(select(AnalysisResult).where(AnalysisResult.ticker == "ZZZLIVE.T")).all()
        notification_rows = db.scalars(select(NotificationLog).where(NotificationLog.ticker == "ZZZLIVE.T")).all()

        assert result["analysis_deleted"] == 0
        assert result["notifications_deleted"] == 0
        assert len(analysis_rows) == 1
        assert len(notification_rows) == 1


def test_delete_test_ticker_removes_test_artifacts() -> None:
    with _make_session() as db:
        generate_test_price_bars(
            db,
            ticker="ZZZTEST.T",
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 1),
            seed=1,
        )
        db.add(
            AnalysisResult(
                ticker="ZZZTEST.T",
                as_of_date=date(2026, 4, 1),
                trend_score=1,
                dip_score=1,
                breakout_score=1,
                total_score=3,
                reasons="seed",
            )
        )
        db.add(
            NotificationLog(
                ticker="ZZZTEST.T",
                timeframe="daily",
                notified_period_key="2026-04-01",
                message="seed",
            )
        )
        db.commit()

        result = delete_test_ticker_data(db, ticker="ZZZTEST.T")
        symbol = db.scalar(select(Symbol).where(Symbol.ticker == "ZZZTEST.T"))
        bars = db.scalars(select(PriceBar).where(PriceBar.ticker == "ZZZTEST.T", PriceBar.source == "synthetic")).all()
        analysis_rows = db.scalars(select(AnalysisResult).where(AnalysisResult.ticker == "ZZZTEST.T")).all()
        notification_rows = db.scalars(select(NotificationLog).where(NotificationLog.ticker == "ZZZTEST.T")).all()

        assert result["bars_deleted"] == 1
        assert result["analysis_deleted"] == 1
        assert result["notifications_deleted"] == 1
        assert result["symbols_deleted"] == 1
        assert symbol is None
        assert len(bars) == 0
        assert len(analysis_rows) == 0
        assert len(notification_rows) == 0
