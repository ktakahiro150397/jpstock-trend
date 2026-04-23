from __future__ import annotations

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.db import SessionLocal
from app.services.ingest_service import ingest_market_data
from app.services.signal_service import run_analysis


def scheduled_ingest() -> None:
    with SessionLocal() as db:
        ingest_market_data(db)


def scheduled_analysis() -> None:
    with SessionLocal() as db:
        run_analysis(db, run_type="weekly")


def main() -> None:
    settings = get_settings()
    scheduler = BlockingScheduler(timezone=settings.timezone)
    trigger = CronTrigger(
        day_of_week=settings.weekly_cron_day_of_week,
        hour=settings.weekly_cron_hour,
        minute=settings.weekly_cron_minute,
    )
    ingest_trigger = CronTrigger(hour=settings.ingest_cron_hour, minute=settings.ingest_cron_minute)
    scheduler.add_job(scheduled_ingest, ingest_trigger, id="daily-ingest", replace_existing=True)
    scheduler.add_job(scheduled_analysis, trigger, id="weekly-analysis", replace_existing=True)
    scheduler.start()


if __name__ == "__main__":
    main()
