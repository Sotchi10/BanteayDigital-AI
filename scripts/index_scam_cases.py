"""Index backend ScamCase records into Qdrant."""

import argparse

from app.config import get_settings
from app.repositories.qdrant_store import QdrantStore
from app.repositories.scam_case_repository import list_scam_cases
from app.services.scam_case_indexer import index_scam_case


def main() -> None:
    parser = argparse.ArgumentParser(description="Index backend ScamCase records")
    parser.add_argument(
        "--include-unverified",
        action="store_true",
        help="Index all cases. Use only for local synthetic test data.",
    )
    args = parser.parse_args()

    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL must be set before indexing ScamCases")

    scam_cases = list_scam_cases(
        settings.database_url,
        verified_only=not args.include_unverified,
    )
    if not scam_cases:
        scope = "verified " if not args.include_unverified else ""
        print(f"No {scope}ScamCase records found to index.")
        return

    store = QdrantStore()
    store.ensure_collection()
    for scam_case in scam_cases:
        index_scam_case(scam_case, store)

    print(f"Indexed {len(scam_cases)} ScamCase record(s).")


if __name__ == "__main__":
    main()
