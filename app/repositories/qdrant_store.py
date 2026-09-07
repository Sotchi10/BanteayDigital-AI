"""Minimal Qdrant storage adapter for the first retrieval proof."""

from collections.abc import Mapping
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import get_settings


class QdrantStore:
    """Stores and searches embeddings in the configured Qdrant collection."""

    def __init__(self) -> None:
        settings = get_settings()
        self.collection_name = settings.qdrant_collection
        self.vector_size = settings.embedding_dimensions
        self.client = QdrantClient(url=str(settings.qdrant_url))

    def ensure_collection(self) -> None:
        """Create the collection or confirm its vector size."""
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                ),
            )
            return

        collection = self.client.get_collection(self.collection_name)
        existing_size = collection.config.params.vectors.size
        if existing_size != self.vector_size:
            raise RuntimeError(
                f"Collection {self.collection_name!r} uses {existing_size} dimensions; "
                f"expected {self.vector_size}. Use a new collection name to change dimensions."
            )

    def upsert(self, point_id: str, embedding: list[float], payload: Mapping[str, Any]) -> None:
        """Insert or replace one point."""
        if len(embedding) != self.vector_size:
            raise ValueError("Vector size does not match the configured collection size")
        self.client.upsert(
            collection_name=self.collection_name,
            wait=True,
            points=[PointStruct(id=point_id, vector=embedding, payload=dict(payload))],
        )

    def search(self, embedding: list[float], limit: int = 3):
        """Return closest vector matches for a query embedding."""
        if len(embedding) != self.vector_size:
            raise ValueError("Vector size does not match the configured collection size")
        return self.client.query_points(
            collection_name=self.collection_name,
            query=embedding,
            limit=limit,
        ).points
