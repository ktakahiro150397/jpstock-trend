from __future__ import annotations

from datetime import date

from app.data_sources.edinet import EdinetDataSource, EdinetDbCalendarEntry


def collect_financial_documents(
    api_key: str,
    target_date: date,
    allowed_doc_types: set[str] | None = None,
) -> list[EdinetDbCalendarEntry]:
    if not api_key:
        raise ValueError("EDINET_API_KEY is required")

    datasource = EdinetDataSource(api_key=api_key)
    return datasource.get_documents(target_date=target_date)
