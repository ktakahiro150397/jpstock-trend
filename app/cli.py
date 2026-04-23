from __future__ import annotations

import argparse
from datetime import datetime

from app.db import SessionLocal
from app.services.ingest_service import ingest_market_data
from app.services.signal_service import run_analysis


def _parse_date(value: str | None):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def main() -> None:
    parser = argparse.ArgumentParser(description="jpstock-trend command interface")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="Fetch Yahoo data and upsert into DB")
    ingest.add_argument("--as-of-date", dest="as_of_date", default=None, help="YYYY-MM-DD")

    analyze = sub.add_parser("analyze", help="Run analysis from persisted OHLC data")
    analyze.add_argument("--as-of-date", dest="as_of_date", default=None, help="YYYY-MM-DD")

    args = parser.parse_args()

    with SessionLocal() as db:
        if args.command == "ingest":
            result = ingest_market_data(db, as_of_date=_parse_date(args.as_of_date))
            print(result)
            return

        if args.command == "analyze":
            result = run_analysis(db, run_type="manual", as_of_date=_parse_date(args.as_of_date))
            print({"count": len(result), "candidates": [r.ticker for r in result if r.status == "entry_candidate"]})
            return


if __name__ == "__main__":
    main()
