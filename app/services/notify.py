from __future__ import annotations

from typing import Iterable

import httpx

from app.analysis import SignalResult


def build_discord_message(results: Iterable[SignalResult]) -> str:
    tickers = [r.ticker for r in results if r.status == "entry_candidate"]
    if not tickers:
        return "今週のエントリー候補はありません。"
    listed = ", ".join(tickers)
    return f"エントリー候補があります（{len(tickers)}件）: {listed}\n詳細はWeb UIで確認してください。"


def send_discord(webhook_url: str, content: str) -> None:
    if not webhook_url:
        return
    with httpx.Client(timeout=10) as client:
        client.post(webhook_url, json={"content": content}).raise_for_status()
