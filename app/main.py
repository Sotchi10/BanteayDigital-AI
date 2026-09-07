"""FastAPI application entry point."""

from fastapi import FastAPI

from app.api.router import router
from app.config import get_settings

# Validate configuration before the application accepts requests.
get_settings()

app = FastAPI(
    title="Banteay Digital AI Service",
    version="0.1.0",
    description="Scam analysis and retrieval service.",
)

app.include_router(router)
