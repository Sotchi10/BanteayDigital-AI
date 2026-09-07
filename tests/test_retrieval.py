from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api import retrieval
from app.config import get_settings
from app.main import app


def test_retrieve_returns_qdrant_matches(monkeypatch) -> None:
    class FakeStore:
        def ensure_collection(self) -> None:
            return None

        def search(self, embedding: list[float], limit: int):
            assert len(embedding) == 768
            assert limit == 1
            return [
                SimpleNamespace(
                    id="case-1",
                    score=0.98,
                    payload={"title": "OTP scam", "riskLevel": "HIGH"},
                )
            ]

    monkeypatch.setattr(retrieval, "embed_text", lambda value: [0.0] * 768)
    monkeypatch.setattr(retrieval, "QdrantStore", FakeStore)

    configured_key = get_settings().ai_service_api_key
    headers = (
        {"X-AI-Service-Key": configured_key.get_secret_value()}
        if configured_key is not None
        else {}
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/retrieve",
            json={"type": "TEXT", "value": "Send your OTP now", "limit": 1},
            headers=headers,
        )

    assert response.status_code == 200
    assert response.json() == {
        "matches": [
            {
                "id": "case-1",
                "score": 0.98,
                "payload": {"title": "OTP scam", "riskLevel": "HIGH"},
            }
        ]
    }
