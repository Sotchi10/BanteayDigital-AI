"""Exercise retrieval and simple AI analysis against the text benchmark.

Requires a running AI service, Gemini credentials, Qdrant, and indexed scam cases.
This checks integration and response validity; human-labelled review is still needed
to measure LLM quality.
"""

import json
import os
from pathlib import Path

import httpx


BENCHMARK_PATH = Path(__file__).resolve().parents[2] / "backend" / "data" / "text_benchmark.json"
SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8000").rstrip("/")


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
                }
                for match in matches
                if match.get("payload", {}).get("kind") == "scam_case"
                and all(field in match["payload"] for field in ("caseId", "title", "scamType", "riskLevel"))
            ]
            analyze = client.post(
                f"{SERVICE_URL}/api/v1/analyze",
                headers=headers(),
                json={
                    "type": "TEXT",
                    "value": case["text"],
                    "deterministicFindings": [],
                    "retrievedCases": retrieved_cases,
                },
            )
            analyze.raise_for_status()
            result = analyze.json()
            outcomes.append(
                {
                    "id": case["id"],
                    "label": case["label"],
                    "matches": len(matches),
                    "assessment": result["assessment"],
                    "hasSummary": bool(result["summary"]),
                    "actionCount": len(result["recommendedActions"]),
                }
            )

    print(json.dumps({"serviceUrl": SERVICE_URL, "cases": len(outcomes), "outcomes": outcomes}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
