"""Schemas for service health responses."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "banteay-ai-service"
