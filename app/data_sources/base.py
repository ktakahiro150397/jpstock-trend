from typing import Protocol

import pandas as pd


class MarketDataSource(Protocol):
    def fetch_ohlcv(self, ticker: str, lookback_days: int) -> pd.DataFrame:
        """Return DataFrame with columns: Open, High, Low, Close, Volume and DatetimeIndex."""
