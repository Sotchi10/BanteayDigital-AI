"""Index one backend ScamCase in Qdrant for local retrieval testing."""

import argparse
from uuid import NAMESPACE_URL, uuid5

from app.config import get_settings
from app.repositories.qdrant_store import QdrantStore
from app.repositories.scam_case_repository import get_scam_case
from app.services.embedding_service import embed_text


def build_document(scam_case: dict) -> str:
    indicators = ", ".join(scam_case["indicators"])
    return "\n".join(
        [
            f"Title: {scam_case['title']}",
            f"Type: {scam_case['scamType']}",
            f"Description: {scam_case['description']}",
            f"Sample text: {scam_case['sampleText']}",
            f"Indicators: {indicators}",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Index one ScamCase in Qdrant")
    parser.add_argument("case_id", type=int)
    args = parser.parse_args()

    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL must be set before indexing a ScamCase")

    scam_case = get_scam_case(settings.database_url, args.case_id)
    embedding = embed_text(build_document(scam_case))
    point_id = str(uuid5(NAMESPACE_URL, f"banteay-digital/scam-case/{scam_case['id']}"))

    store = QdrantStore()
    store.ensure_collection()
    store.upsert(
        point_id=point_id,
        embedding=embedding,
        payload={
            "kind": "scam_case",
            "caseId": scam_case["id"],
            "title": scam_case["title"],
            "scamType": scam_case["scamType"],
            "riskLevel": scam_case["riskLevel"],
            "source": scam_case["source"],
            "verified": scam_case["verified"],
        },
    )
    print(f"Indexed ScamCase {scam_case['id']}: {scam_case['title']}")


if __name__ == "__main__":
    main()
