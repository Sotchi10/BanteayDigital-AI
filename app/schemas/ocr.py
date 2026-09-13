from pydantic import BaseModel, Field


class OcrResponse(BaseModel):
    """Text extracted from one uploaded scan image."""

    text: str
    languages: str
    character_count: int = Field(ge=0)
