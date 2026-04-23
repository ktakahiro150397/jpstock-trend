from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class SignalResult:
    ticker: str
    trend_score: int
    dip_score: int
    breakout_score: int
    total_score: int
    status: str
    reasons: list[str]


def _resample(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    rule = {"weekly": "W-FRI", "monthly": "ME"}[timeframe]
    agg = {
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }
    return df.resample(rule).agg(agg).dropna()


def _calc_trend_score(df_weekly: pd.DataFrame, df_monthly: pd.DataFrame, reasons: list[str]) -> int:
    score = 0
    for name, frame in (("週足", df_weekly), ("月足", df_monthly)):
        if len(frame) < 60:
            continue
        ma50 = frame["Close"].rolling(50).mean()
        ma200 = frame["Close"].rolling(200).mean()

        close = frame["Close"].iloc[-1]
        if close > ma200.iloc[-1]:
            score += 10
            reasons.append(f"{name}: 終値がMA200を上回る")
        if ma50.iloc[-1] > ma200.iloc[-1]:
            score += 10
            reasons.append(f"{name}: MA50がMA200を上回る")

    highs = df_weekly["High"].tail(12)
    lows = df_weekly["Low"].tail(12)
    if len(highs) >= 6:
        if highs.iloc[-1] >= highs.quantile(0.75):
            score += 10
            reasons.append("週足: 高値が直近レンジ上位")
        if lows.iloc[-1] >= lows.median():
            score += 10
            reasons.append("週足: 安値切り上げ傾向")

    return min(score, 40)


def _calc_dip_score(df_daily: pd.DataFrame, reasons: list[str]) -> int:
    if len(df_daily) < 120:
        return 0

    score = 0
    close = df_daily["Close"]
    ma20 = close.rolling(20).mean()
    ma50 = close.rolling(50).mean()

    recent_high = close.tail(60).max()
    current = close.iloc[-1]
    drawdown = (recent_high - current) / recent_high * 100
    if 3 <= drawdown <= 15:
        score += 12
        reasons.append(f"日足: 直近高値から{drawdown:.1f}%の調整")

    if ma50.iloc[-1] <= current <= ma20.iloc[-1] * 1.03:
        score += 12
        reasons.append("日足: MA20-50付近で下げ止まり")

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss.replace(0, 1e-9)
    rsi = 100 - (100 / (1 + rs))

    if len(rsi.dropna()) >= 5 and rsi.tail(5).min() < 45 and rsi.iloc[-1] > rsi.iloc[-2] > rsi.iloc[-3]:
        score += 11
        reasons.append("日足: RSIが反転上昇")

    return min(score, 35)


def _calc_breakout_score(df_daily: pd.DataFrame, reasons: list[str]) -> int:
    if len(df_daily) < 80:
        return 0

    score = 0
    close = df_daily["Close"]
    high = df_daily["High"]
    volume = df_daily["Volume"]

    prev_high = high.tail(40).max()
    dist = (prev_high - close.iloc[-1]) / prev_high * 100
    if 0 <= dist <= 3:
        score += 10
        reasons.append(f"日足: 直近高値まで{dist:.1f}%")

    if close.iloc[-1] > close.rolling(5).max().iloc[-2]:
        score += 8
        reasons.append("日足: 5日高値更新")

    vol_ma20 = volume.rolling(20).mean()
    if vol_ma20.iloc[-1] > 0 and volume.iloc[-1] / vol_ma20.iloc[-1] >= 1.2:
        score += 7
        reasons.append("日足: 反発局面で出来高増")

    return min(score, 25)


def analyze_symbol(ticker: str, daily_df: pd.DataFrame, threshold: int = 70) -> SignalResult:
    if daily_df.empty:
        return SignalResult(ticker, 0, 0, 0, 0, "no_data", ["価格データなし"])

    df_daily = daily_df.copy().sort_index()
    df_weekly = _resample(df_daily, "weekly")
    df_monthly = _resample(df_daily, "monthly")

    reasons: list[str] = []
    trend_score = _calc_trend_score(df_weekly, df_monthly, reasons)
    dip_score = _calc_dip_score(df_daily, reasons)
    breakout_score = _calc_breakout_score(df_daily, reasons)

    total = trend_score + dip_score + breakout_score
    status = "entry_candidate" if total >= threshold else "watch"

    return SignalResult(
        ticker=ticker,
        trend_score=trend_score,
        dip_score=dip_score,
        breakout_score=breakout_score,
        total_score=total,
        status=status,
        reasons=reasons,
    )
