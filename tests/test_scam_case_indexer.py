from app.services import scam_case_indexer


def test_index_scam_case_uses_a_stable_point_and_complete_payload(monkeypatch) -> None:
    class FakeStore:
        def __init__(self) -> None:
            self.upserted = None

        def upsert(self, point_id: str, embedding: list[float], payload: dict) -> None:
            self.upserted = (point_id, embedding, payload)

    scam_case = {
        "id": 7,
        "title": "Fake bank reward",
        "scamType": "phishing",
        "description": "A fake banking prize message.",
        "sampleText": "You won a reward.",
        "indicators": ["prize", "bank impersonation"],
        "riskLevel": "HIGH",
        "source": "test",
        "verified": True,
    }
    store = FakeStore()
    monkeypatch.setattr(scam_case_indexer, "embed_document", lambda document: [0.0] * 768)

    scam_case_indexer.index_scam_case(scam_case, store)

    point_id, embedding, payload = store.upserted
    assert point_id == "ddf53932-5286-5c13-91eb-0fcdbce76986"
    assert embedding == [0.0] * 768
    assert payload == {
        "kind": "scam_case",
        "caseId": 7,
        "title": "Fake bank reward",
        "scamType": "phishing",
        "riskLevel": "HIGH",
        "source": "test",
        "verified": True,
    }
