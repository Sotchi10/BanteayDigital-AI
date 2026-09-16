"""Measure live LLM behavior on scam patterns outside the seed catalogue.

Requires a running AI service, Gemini credentials, Qdrant, and indexed scam
cases. The backend unit tests separately verify enforcement of model signals.
"""

import json
import os
import sys
from pathlib import Path

import httpx


BENCHMARK_PATH = Path(
    os.getenv(
        "NOVEL_SCAM_BENCHMARK_PATH",
        Path(__file__).resolve().parents[1] / "data" / "novel_text_benchmark.json",
    )
)
SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8000").rstrip("/")
ASSESSMENT_RANK = {
    "NO_STRONG_WARNING_SIGNS": 0,
    "INSUFFICIENT_EVIDENCE": 0,
    "CAUTION": 1,
    "SUSPICIOUS": 2,
    "STRONG_SCAM_INDICATORS": 3,
}


def headers() -> dict[str, str]:
    key = os.getenv("AI_SERVICE_API_KEY")
    return {"X-AI-Service-Key": key} if key else {}


def main() -> None:
    cases = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    outcomes: list[dict[str, object]] = []

    with httpx.Client(timeout=20) as client:
        for case in cases:
            retrieve = client.post(
                f"{SERVICE_URL}/api/v1/retrieve",
                headers=headers(),
                json={"type": "TEXT", "value": case["text"], "limit": 3},
            )
            retrieve.raise_for_status()
            matches = retrieve.json()["matches"]
            retrieved_cases = [
                {
                    "caseId": match["payload"]["caseId"],
                    "title": match["payload"]["title"],
                    "scamType": match["payload"]["scamType"],
                    "riskLevel": match["payload"]["riskLevel"],
                    "score": match["score"],
                    "verified": bool(match["payload"].get("verified")),
                    "description": match["payload"].get("description"),
                    "sampleText": match["payload"].get("sampleText"),
                    "indicators": match["payload"].get("indicators", []),
                }
                for match in matches
                if match.get("payload", {}).get("kind") == "scam_case"
                and all(field in match["payload"] for field in ("caseId", "title", "scamType", "riskLevel"))
            ]
            top_similarity = max((match["score"] for match in matches), default=None)
            analyze = client.post(
                f"{SERVICE_URL}/api/v1/analyze",
                headers=headers(),
                json={
                    "type": "TEXT",
                    "value": case["text"],
                    "language": case.get("language", "en"),
                    "deterministicFindings": [],
                    "retrievedCases": retrieved_cases,
                    "retrievalStatus": "AVAILABLE",
                    "topSimilarity": top_similarity,
                },
            )
            analyze.raise_for_status()
            result = analyze.json()
            risk_signals = result.get("riskSignals", [])
            grounded_signals = all(
                isinstance(signal.get("evidence"), str)
                and signal["evidence"].casefold() in case["text"].casefold()
                for signal in risk_signals
            )
            minimum_rank = ASSESSMENT_RANK[case["minimumAssessment"]]
            if case["label"] == "SCAM":
                passed = (
                    ASSESSMENT_RANK.get(result["assessment"], -1) >= minimum_rank
                    and len(risk_signals) > 0
                    and grounded_signals
                )
            else:
                passed = result["assessment"] in case.get("allowedAssessments", []) and not risk_signals
            outcomes.append(
                {
                    "id": case["id"],
                    "label": case["label"],
                    "matches": len(matches),
                    "topSimilarity": top_similarity,
                    "assessment": result["assessment"],
                    "minimumAssessment": case["minimumAssessment"],
                    "riskSignalCount": len(risk_signals),
                    "groundedSignals": grounded_signals,
                    "passed": passed,
                }
            )

    passed_count = sum(bool(outcome["passed"]) for outcome in outcomes)
    report = {
        "serviceUrl": SERVICE_URL,
        "benchmark": str(BENCHMARK_PATH),
        "cases": len(outcomes),
        "passed": passed_count,
        "failed": len(outcomes) - passed_count,
        "passRate": round(passed_count / len(outcomes), 3) if outcomes else 0,
        "outcomes": outcomes,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if "--strict" in sys.argv and passed_count != len(outcomes):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
