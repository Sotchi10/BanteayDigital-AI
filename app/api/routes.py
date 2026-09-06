"""Routes exposed by the AI service."""

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
def health_check() -> HealthResponse:
    """Return process health without contacting future external dependencies."""
    settings = get_settings()
    return HealthResponse(environment=settings.environment)

