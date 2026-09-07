"""Index one backend ScamCase in Qdrant for local retrieval testing."""

import argparse

from app.config import get_settings
from app.repositories.qdrant_store import QdrantStore
from app.repositories.scam_case_repository import get_scam_case
from app.services.scam_case_indexer import index_scam_case


def main() -> None:
    parser = argparse.ArgumentParser(description="Index one ScamCase in Qdrant")
    parser.add_argument("case_id", type=int)
    args = parser.parse_args()

    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL must be set before indexing a ScamCase")

    scam_case = get_scam_case(settings.database_url, args.case_id)
    store = QdrantStore()
    store.ensure_collection()
    index_scam_case(scam_case, store)
    print(f"Indexed ScamCase {scam_case['id']}: {scam_case['title']}")


if __name__ == "__main__":
    main()
