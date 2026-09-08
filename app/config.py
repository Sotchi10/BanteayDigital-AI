"""Environment-backed application settings."""

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration shared by the API and future AI integrations."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    port: int = Field(default=8000, ge=1, le=65535)

    ai_service_api_key: SecretStr | None = None
    qdrant_url: AnyHttpUrl = "http://localhost:6333"
    qdrant_collection: str = Field(default="scam_knowledge_v1", min_length=1)
    retrieval_min_score: float = Field(default=0.70, ge=0, le=1)
    retrieval_verified_only: bool | None = None
    database_url: str | None = None

    gemini_api_key: SecretStr | None = None
    gemini_model: str = Field(default="gemini-3.5-flash-lite", min_length=1)
    embedding_model: str = Field(default="gemini-embedding-001", min_length=1)
    embedding_dimensions: int = Field(default=768, ge=1)

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.environment == "production" and self.ai_service_api_key is None:
            raise ValueError("AI_SERVICE_API_KEY must be set when ENVIRONMENT=production")
        # Local synthetic data is often unverified. Production retrieval must
        # use the moderated catalogue unless explicitly configured otherwise.
        if self.retrieval_verified_only is None:
            self.retrieval_verified_only = self.environment == "production"
        return self


@lru_cache
def get_settings() -> Settings:
    """Load settings once per process."""
    return Settings()
