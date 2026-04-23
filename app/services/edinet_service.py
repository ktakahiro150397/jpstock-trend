from __future__ import annotations

from datetime import date

from app.data_sources.edinet import EdinetDataSource, EdinetDocument

FINANCIAL_DOC_TYPES = {"120", "130", "140"}


def collect_financial_documents(
    api_key: str,
    target_date: date,
    allowed_doc_types: set[str] | None = None,
) -> list[EdinetDocument]:
    if not api_key:
        raise ValueError("EDINET_API_KEY is required")

    datasource = EdinetDataSource(api_key=api_key)
    all_docs = datasource.get_documents(target_date=target_date, include_list=True)
    filter_set = allowed_doc_types or FINANCIAL_DOC_TYPES
    return [
        doc
        for doc in all_docs
        if doc.doc_type_code in filter_set and doc.csv_flag == "1" and (doc.sec_code is not None)
    ]
