"""Embed, store, and retrieve one deterministic smoke-test document."""

from uuid import NAMESPACE_URL, uuid5

from app.repositories.qdrant_store import QdrantStore
from app.services.embedding_service import embed_text

SAMPLE_TEXT = (
    "Urgent bank security alert: send your one-time password now "
    "or your account will be locked."
)
POINT_ID = str(uuid5(NAMESPACE_URL, "banteay-digital/rag-smoke-test-v1"))


def main() -> None:
    store = QdrantStore()
    store.ensure_collection()
    vector = embed_text(SAMPLE_TEXT)
    store.upsert(
        point_id=POINT_ID,
        embedding=vector,
        payload={
            "kind": "smoke_test",
            "text": SAMPLE_TEXT,
            "source": "scripts/verify_retrieval.py",
        },
    )

    matches = store.search(vector, limit=1)
    if not matches or str(matches[0].id) != POINT_ID:
        raise RuntimeError("Qdrant did not return the inserted smoke-test vector")

    print(
        "RAG smoke test passed: "
        f"point={matches[0].id}, score={matches[0].score:.4f}, "
        f"collection={store.collection_name}"
    )


if __name__ == "__main__":
    main()
