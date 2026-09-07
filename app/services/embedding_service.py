"""Gemini embedding adapter used by the first retrieval foundation."""

from google import genai
from google.genai import types

from app.config import get_settings


class EmbeddingError(RuntimeError):
    """Raised when Gemini cannot create a valid embedding."""


def embed_text(text: str) -> list[float]:
    """Create an embedding for one text value."""
    if not text.strip():
        raise ValueError("Text to embed must not be empty")

    settings = get_settings()
    if settings.gemini_api_key is None:
        raise EmbeddingError("GEMINI_API_KEY must be configured before generating embeddings")

    client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
    result = client.models.embed_content(
        model=settings.embedding_model,
        contents=text,
        config=types.EmbedContentConfig(
            output_dimensionality=settings.embedding_dimensions,
        ),
    )

    if not result.embeddings:
        raise EmbeddingError("Gemini returned no embedding")

    embedding = list(result.embeddings[0].values)
    if len(embedding) != settings.embedding_dimensions:
        raise EmbeddingError(
            "Embedding size does not match EMBEDDING_DIMENSIONS "
            f"({len(embedding)} != {settings.embedding_dimensions})"
        )
    return embedding
