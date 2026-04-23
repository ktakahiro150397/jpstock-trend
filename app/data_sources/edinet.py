from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass
class EdinetDocument:
    doc_id: str
    edinet_code: str
    sec_code: str | None
    filer_name: str
    doc_type_code: str
    form_code: str
    submit_date_time: str
    csv_flag: str | None
    xbrl_flag: str | None


class EdinetDataSource:
    """Lightweight wrapper around EDINET API v2.

    API docs (FSA): https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/download/ESE140206.pdf
    """

    def __init__(self, api_key: str, base_url: str = "https://api.edinet-fsa.go.jp/api/v2") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def get_documents(self, target_date: date, include_list: bool = True) -> list[EdinetDocument]:
        params = {
            "date": target_date.isoformat(),
            "Subscription-Key": self.api_key,
        }
        if include_list:
            params["type"] = "2"

        url = f"{self.base_url}/documents.json?{urlencode(params)}"
        req = Request(url, headers={"User-Agent": "jpstock-trend/0.1"})

        with urlopen(req, timeout=30) as response:  # noqa: S310 (EDINET official endpoint)
            payload = json.loads(response.read().decode("utf-8"))

        return parse_documents_response(payload)


def parse_documents_response(payload: dict[str, Any]) -> list[EdinetDocument]:
    results = payload.get("results") or []
    documents: list[EdinetDocument] = []
    for item in results:
        doc_id = str(item.get("docID") or "").strip()
        if not doc_id:
            continue
        documents.append(
            EdinetDocument(
                doc_id=doc_id,
                edinet_code=str(item.get("edinetCode") or "").strip(),
                sec_code=(str(item.get("secCode")).strip() if item.get("secCode") else None),
                filer_name=str(item.get("filerName") or "").strip(),
                doc_type_code=str(item.get("docTypeCode") or "").strip(),
                form_code=str(item.get("formCode") or "").strip(),
                submit_date_time=str(item.get("submitDateTime") or "").strip(),
                csv_flag=(str(item.get("csvFlag")).strip() if item.get("csvFlag") is not None else None),
                xbrl_flag=(str(item.get("xbrlFlag")).strip() if item.get("xbrlFlag") is not None else None),
            )
        )
    return documents
