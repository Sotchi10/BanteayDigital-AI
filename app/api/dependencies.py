"""Shared API dependencies."""

from hmac import compare_digest

from fastapi import Header, HTTPException, status

from app.config import get_settings


def require_service_key(x_ai_service_key: str | None = Header(default=None)) -> None:
    """Require the shared key when one is configured for this service."""
    configured_key = get_settings().ai_service_api_key
    if configured_key is None:
        return

    if x_ai_service_key is None or not compare_digest(
        x_ai_service_key,
        configured_key.get_secret_value(),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid AI service key",
        )
