from app.data_sources.edinet import parse_documents_response
from app.services.edinet_service import collect_financial_documents


def test_parse_documents_response_skips_empty_doc_id() -> None:
    payload = {
        "results": [
            {"docID": "", "edinetCode": "E00001"},
            {
                "docID": "S100TEST",
                "edinetCode": "E00002",
                "secCode": "72030",
                "filerName": "Test Corp",
                "docTypeCode": "120",
                "formCode": "030000",
                "submitDateTime": "2026-04-01 09:00",
                "csvFlag": "1",
                "xbrlFlag": "1",
            },
        ]
    }

    docs = parse_documents_response(payload)

    assert len(docs) == 1
    assert docs[0].doc_id == "S100TEST"
    assert docs[0].sec_code == "72030"


def test_collect_financial_documents_filters_doc_types_and_csv(monkeypatch) -> None:
    class DummySource:
        def __init__(self, api_key: str):
            self.api_key = api_key

        def get_documents(self, target_date, include_list=True):
            return parse_documents_response(
                {
                    "results": [
                        {"docID": "A", "docTypeCode": "120", "csvFlag": "1", "secCode": "72030"},
                        {"docID": "B", "docTypeCode": "140", "csvFlag": "0", "secCode": "72030"},
                        {"docID": "C", "docTypeCode": "170", "csvFlag": "1", "secCode": "72030"},
                    ]
                }
            )

    monkeypatch.setattr("app.services.edinet_service.EdinetDataSource", DummySource)

    from datetime import date

    docs = collect_financial_documents(api_key="dummy", target_date=date(2026, 4, 1))

    assert [d.doc_id for d in docs] == ["A"]
