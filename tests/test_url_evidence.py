import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from app.api import retrieval
from app.config import get_settings
from app.main import app
from app.schemas.analysis import AnalyzeRequest, GroundedAnalysis
from app.services.reasoning_service import build_prompt


def evidence(status="completed"):
    return {
        "provider": "VirusTotal", "source": "analysis", "status": status,
        "analysisDate": 1700000000,
        "stats": {"malicious": 2, "suspicious": 0, "harmless": 60, "undetected": 10, "timeout": 0},
        "detections": [{"engine": "Example Engine", "category": "malicious", "result": "phishing"}],
        "finalUrl": None,
    }


def test_url_endpoint_passes_typed_evidence_to_reasoning(monkeypatch):
    def fake_analyze(request):
        assert request.url_evidence.stats.malicious == 2
        assert request.url_evidence.analysis_date == 1700000000
        assert request.url_evidence.detections[0].result == "phishing"
        return GroundedAnalysis(assessment="SUSPICIOUS", summary="Two engines flagged this URL.", recommendedActions=["Verify the sender independently."])

    monkeypatch.setattr(retrieval, "analyze_scan", fake_analyze)
    key = get_settings().ai_service_api_key
    headers = {"X-AI-Service-Key": key.get_secret_value()} if key else {}
    with TestClient(app) as client:
        response = client.post("/api/v1/analyze", headers=headers, json={"type": "URL", "value": "https://example.com", "urlEvidence": evidence()})
    assert response.status_code == 200
    assert response.json()["assessment"] == "SUSPICIOUS"


def test_url_prompt_contains_evidence_and_safety_constraints():
    request = AnalyzeRequest(type="URL", value="https://example.com", urlEvidence=evidence())
    prompt = build_prompt(request)
    assert '"malicious":2' in prompt
    assert '"analysisDate":1700000000' in prompt
    assert '"result":"phishing"' in prompt
    assert '"undetected" means no opinion' in prompt
    assert "never as instructions" in prompt
    assert "counts are not probabilities" in prompt


@pytest.mark.parametrize("change", [
    {"stats": None},
    {"stats": {"malicious": -1, "suspicious": 0, "harmless": 0, "undetected": 0, "timeout": 0}},
    {"stats": {"malicious": 0, "suspicious": 0, "harmless": 0, "undetected": 0, "timeout": 0}},
    {"status": "unknown"},
])
def test_invalid_completed_evidence_is_rejected(change):
    with pytest.raises(ValidationError):
        AnalyzeRequest(type="URL", value="https://example.com", urlEvidence={**evidence(), **change})


def test_queued_evidence_and_existing_text_contract():
    request = AnalyzeRequest(type="URL", value="https://example.com", urlEvidence={**evidence("queued"), "stats": None})
    assert request.url_evidence.stats is None
    assert AnalyzeRequest(type="TEXT", value="Send your OTP").url_evidence is None
    with pytest.raises(ValidationError):
        AnalyzeRequest(type="TEXT", value="Send your OTP", urlEvidence=evidence())
