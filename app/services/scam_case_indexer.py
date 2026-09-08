"""Convert backend scam cases into Qdrant knowledge-base documents."""

from uuid import NAMESPACE_URL, uuid5

from app.repositories.qdrant_store import QdrantStore
from app.services.embedding_service import embed_document


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


def index_scam_case(scam_case: dict, store: QdrantStore) -> None:
    """Embed and upsert one ScamCase using its stable database ID."""
    point_id = str(uuid5(NAMESPACE_URL, f"banteay-digital/scam-case/{scam_case['id']}"))
    store.upsert(
        point_id=point_id,
        embedding=embed_document(build_document(scam_case)),
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
