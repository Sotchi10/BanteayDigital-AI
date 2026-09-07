from typing import Any, Literal

from pydantic import BaseModel, Field


class RetrieveRequest(BaseModel):
    type: Literal["TEXT", "URL"]
    value: str = Field(min_length=1, max_length=10_000)
    limit: int = Field(default=3, ge=1, le=10)


class RetrievedMatch(BaseModel):
    id: str
    score: float
    payload: dict[str, Any]


class RetrieveResponse(BaseModel):
    matches: list[RetrievedMatch]
