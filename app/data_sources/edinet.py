from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from urllib.request import Request, urlopen


@dataclass
class EdinetDbCalendarEntry:
    sec_code: str
    company_name: str
    announcement_date: str
    period_type: str
    fiscal_year_end: str
    industry: str
    market_segment: str


class EdinetDataSource:
    """Lightweight wrapper around EDINET DB API v1 (edinetdb.jp)."""

    def __init__(self, api_key: str, base_url: str = "https://edinetdb.jp/v1") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def get_calendar(self) -> list[EdinetDbCalendarEntry]:
        url = f"{self.base_url}/calendar"
        req = Request(url, headers={
            "User-Agent": "jpstock-trend/0.1",
            "X-API-Key": self.api_key,
        })
        with urlopen(req, timeout=30) as response:  # noqa: S310 (edinetdb.jp official endpoint)
            payload = json.loads(response.read().decode("utf-8"))
        return _parse_calendar_response(payload)

    def get_documents(self, target_date: date, include_list: bool = True) -> list[EdinetDbCalendarEntry]:
        """Compat shim: returns calendar entries filtered to target_date."""
        all_entries = self.get_calendar()
        target = target_date.isoformat()
        return [e for e in all_entries if e.announcement_date == target]


def _parse_calendar_response(payload: dict) -> list[EdinetDbCalendarEntry]:
    entries = (payload.get("data") or {}).get("calendar") or []
    result: list[EdinetDbCalendarEntry] = []
    for item in entries:
        sec_code = str(item.get("secCode") or "").strip()
        if not sec_code:
            continue
        result.append(EdinetDbCalendarEntry(
            sec_code=sec_code,
            company_name=str(item.get("companyName") or "").strip(),
            announcement_date=str(item.get("announcementDate") or "").strip(),
            period_type=str(item.get("periodType") or "").strip(),
            fiscal_year_end=str(item.get("fiscalYearEnd") or "").strip(),
            industry=str(item.get("industry") or "").strip(),
            market_segment=str(item.get("marketSegment") or "").strip(),
        ))
    return result
