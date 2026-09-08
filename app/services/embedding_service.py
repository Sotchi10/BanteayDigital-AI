"""Gemini embedding adapter used by the first retrieval foundation."""

from google import genai
from google.genai import types

from app.config import get_settings


class EmbeddingError(RuntimeError):
    """Raised when Gemini cannot create a valid embedding."""


def embed_text(text: str, *, task_type: str | None = None) -> list[float]:
    """Create an embedding for a query or a knowledge-base document."""
    if not text.strip():
        raise ValueError("Text to embed must not be empty")

    settings = get_settings()
    if settings.gemini_api_key is None:
        raise EmbeddingError("GEMINI_API_KEY must be configured before generating embeddings")

    try:
        client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
        config = types.EmbedContentConfig(
            output_dimensionality=settings.embedding_dimensions,
            task_type=task_type,
        )
        result = client.models.embed_content(
            model=settings.embedding_model,
            contents=text,
            config=config,
        )
    except Exception as error:
        raise EmbeddingError("Gemini could not create an embedding") from error

    if not result.embeddings:
        raise EmbeddingError("Gemini returned no embedding")

    embedding = list(result.embeddings[0].values)
    if len(embedding) != settings.embedding_dimensions:
        raise EmbeddingError(
            "Embedding size does not match EMBEDDING_DIMENSIONS "
            f"({len(embedding)} != {settings.embedding_dimensions})"
        )
    return embedding


def embed_query(text: str) -> list[float]:
    """Embed user input as a retrieval query."""
    return embed_text(text, task_type="RETRIEVAL_QUERY")


def embed_document(text: str) -> list[float]:
    """Embed a scam-case record as retrieval knowledge."""
    return embed_text(text, task_type="RETRIEVAL_DOCUMENT")
