from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pandas as pd
import yfinance as yf


class YahooFinanceDataSource:
    def fetch_ohlcv(self, ticker: str, lookback_days: int, as_of_date: date | None = None) -> pd.DataFrame:
        end_base = datetime.now(timezone.utc) if as_of_date is None else datetime.combine(as_of_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end = end_base + timedelta(days=1)
        start = end - timedelta(days=lookback_days)
        df = yf.download(ticker, start=start.date().isoformat(), end=end.date().isoformat(), auto_adjust=True)
        if df.empty:
            return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        return df[["Open", "High", "Low", "Close", "Volume"]].dropna()
