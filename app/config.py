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
    host: str = Field(default="127.0.0.1", min_length=1)
    port: int = Field(default=8000, ge=1, le=65535)

    ai_service_api_key: SecretStr | None = None
    qdrant_url: AnyHttpUrl = "http://localhost:6333"
    qdrant_api_key: SecretStr | None = None
    qdrant_timeout_seconds: float = Field(default=10, gt=0, le=60)
    qdrant_collection: str = Field(default="scam_knowledge_v1", min_length=1)
    retrieval_min_score: float = Field(default=0.70, ge=0, le=1)
    retrieval_verified_only: bool | None = None
    database_url: str | None = None

    gemini_api_key: SecretStr | None = None
    gemini_model: str = Field(default="gemini-3.5-flash-lite", min_length=1)
    gemini_timeout_ms: int = Field(default=30_000, ge=1_000, le=120_000)
    embedding_model: str = Field(default="gemini-embedding-001", min_length=1)
    embedding_dimensions: int = Field(default=768, ge=1)

    tesseract_cmd: str | None = None
    ocr_languages: str = Field(default="eng", min_length=1)
    ocr_tessdata_dir: str | None = None
    ocr_timeout_seconds: int = Field(default=20, ge=1, le=120)
    ocr_max_image_bytes: int = Field(default=10 * 1024 * 1024, ge=1, le=25 * 1024 * 1024)
    ocr_max_image_pixels: int = Field(default=25_000_000, ge=1, le=100_000_000)
    ocr_max_concurrency: int = Field(default=2, ge=1, le=16)
    ai_max_concurrency: int = Field(default=8, ge=1, le=64)
    max_request_bytes: int = Field(default=12 * 1024 * 1024, ge=1024, le=30 * 1024 * 1024)
    allowed_hosts: str = "localhost,127.0.0.1,testserver"

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.environment == "production":
            secrets = {
                "AI_SERVICE_API_KEY": self.ai_service_api_key,
                "QDRANT_API_KEY": self.qdrant_api_key,
                "GEMINI_API_KEY": self.gemini_api_key,
            }
            for name, secret in secrets.items():
                if secret is None or len(secret.get_secret_value()) < 32:
                    raise ValueError(f"{name} must be at least 32 characters in production")
            if self.database_url:
                from urllib.parse import parse_qs, urlparse

                parameters = parse_qs(urlparse(self.database_url).query)
                if parameters.get("sslaccept") != ["strict"]:
                    raise ValueError("Production DATABASE_URL must include sslaccept=strict")
            hosts = self.allowed_host_list
            if not hosts or "*" in hosts:
                raise ValueError("ALLOWED_HOSTS must explicitly list trusted hosts in production")
        # Local synthetic data is often unverified. Production retrieval must
        # use the moderated catalogue unless explicitly configured otherwise.
        if self.retrieval_verified_only is None:
            self.retrieval_verified_only = self.environment == "production"
        return self

    @property
    def allowed_host_list(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]


@lru_cache
def get_settings() -> Settings:
    """Load settings once per process."""
    return Settings()
