from __future__ import annotations

import argparse
from datetime import datetime

from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.services.edinet_service import collect_financial_documents
from app.services.ingest_service import ingest_market_data
from app.services.signal_service import run_analysis
from app.services.test_data_service import delete_test_ticker_data, generate_test_price_bars


def _parse_date(value: str | None):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def main() -> None:
    Base.metadata.create_all(bind=engine)

    parser = argparse.ArgumentParser(description="jpstock-trend command interface")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="Fetch Yahoo data and upsert into DB")
    ingest.add_argument("--as-of-date", dest="as_of_date", default=None, help="YYYY-MM-DD")

    analyze = sub.add_parser("analyze", help="Run analysis from persisted OHLC data")
    analyze.add_argument("--as-of-date", dest="as_of_date", default=None, help="YYYY-MM-DD")

    test_generate = sub.add_parser("test-generate", help="Generate synthetic random-walk bars for a test ticker")
    test_generate.add_argument("--ticker", required=True)
    test_generate.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    test_generate.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    test_generate.add_argument("--start-price", type=float, default=1000.0)
    test_generate.add_argument("--drift", type=float, default=0.0002)
    test_generate.add_argument("--volatility", type=float, default=0.02)
    test_generate.add_argument("--seed", type=int, default=None)

    test_delete = sub.add_parser("test-delete", help="Delete synthetic test ticker data")
    test_delete.add_argument("--ticker", required=True)

    edinet_scan = sub.add_parser("edinet-scan", help="Scan EDINET financial filing candidates by date")
    edinet_scan.add_argument("--date", dest="target_date", required=True, help="YYYY-MM-DD")

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

        if args.command == "test-generate":
            result = generate_test_price_bars(
                db,
                ticker=args.ticker.strip().upper(),
                start_date=_parse_date(args.start_date),
                end_date=_parse_date(args.end_date),
                start_price=args.start_price,
                drift=args.drift,
                volatility=args.volatility,
                seed=args.seed,
            )
            print(result)
            return

        if args.command == "test-delete":
            result = delete_test_ticker_data(db, ticker=args.ticker.strip().upper())
            print(result)
            return

        if args.command == "edinet-scan":
            settings = get_settings()
            docs = collect_financial_documents(
                api_key=settings.edinet_api_key,
                target_date=_parse_date(args.target_date),
            )
            print({"date": args.target_date, "count": len(docs), "sample": [d.doc_id for d in docs[:10]]})
            return


if __name__ == "__main__":
    main()
