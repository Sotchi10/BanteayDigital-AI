from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api import retrieval
from app.schemas.analysis import GroundedAnalysis
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

    def fake_embed_query(value: str) -> list[float]:
        assert value == "Scan type: TEXT\nContent: Send your OTP now"
        return [0.0] * 768

    monkeypatch.setattr(retrieval, "embed_query", fake_embed_query)
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


def test_retrieval_query_labels_the_input_type() -> None:
    request = retrieval.RetrieveRequest(type="URL", value=" https://example.test/login ")

    assert retrieval.build_retrieval_query(request) == (
        "Scan type: URL\nContent: https://example.test/login"
    )


def test_analyze_returns_grounded_json(monkeypatch) -> None:
    configured_key = get_settings().ai_service_api_key
    headers = (
        {"X-AI-Service-Key": configured_key.get_secret_value()}
        if configured_key is not None
        else {}
    )
    monkeypatch.setattr(
        retrieval,
        "analyze_scan",
        lambda request: GroundedAnalysis(
            assessment="SUSPICIOUS",
            evidenceSufficiency="SUFFICIENT",
            riskSignals=[
                {
                    "category": "CREDENTIAL_THEFT",
                    "severity": "CRITICAL",
                    "evidence": "Send your OTP now",
                    "message": "The message asks for an OTP.",
                }
            ],
            summary="The scan asks for an OTP and resembles the retrieved case.",
            recommendedActions=["Do not share your OTP."],
        ),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/analyze",
            headers=headers,
            json={
                "type": "TEXT",
                "value": "Send your OTP now",
                "deterministicFindings": [],
                "retrievedCases": [
                    {
                        "caseId": 1,
                        "title": "OTP scam",
                        "scamType": "phishing",
                        "riskLevel": "HIGH",
                        "score": 0.9,
                        "verified": False,
                    }
                ],
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "assessment": "SUSPICIOUS",
        "evidenceSufficiency": "SUFFICIENT",
        "riskSignals": [
            {
                "category": "CREDENTIAL_THEFT",
                "severity": "CRITICAL",
                "evidence": "Send your OTP now",
                "message": "The message asks for an OTP.",
            }
        ],
        "summary": "The scan asks for an OTP and resembles the retrieved case.",
        "recommendedActions": ["Do not share your OTP."],
    }


def test_analysis_prompt_uses_requested_explanation_language() -> None:
    from app.schemas.analysis import AnalyzeRequest
    from app.services.reasoning_service import build_prompt

    prompt = build_prompt(AnalyzeRequest(type="TEXT", value="Send your OTP", language="km"))

    assert "summary and every recommended action in Khmer" in prompt


def test_analysis_prompt_treats_missing_retrieval_as_unknown_not_safe() -> None:
    from app.schemas.analysis import AnalyzeRequest
    from app.services.reasoning_service import build_prompt

    prompt = build_prompt(
        AnalyzeRequest(
            type="TEXT",
            value="Move the balance into a digital voucher and send me the code.",
            retrievalStatus="AVAILABLE",
            topSimilarity=None,
        )
    )

    assert "No retrieved cases" in prompt
    assert "must never be treated as evidence that content is safe" in prompt
    assert "NO_STRONG_WARNING_SIGNS" in prompt
    assert "affirmatively benign" in prompt
    assert "Retrieval status: AVAILABLE" in prompt
