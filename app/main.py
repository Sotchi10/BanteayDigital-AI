"""FastAPI application entry point."""

from fastapi import FastAPI

from app.api.routes import router
from app.config import get_settings

# Load settings on startup so invalid production configuration stops the service
# before it can accept requests.
settings = get_settings()

app = FastAPI(
    title="Banteay Digital AI Service",
    version="0.1.0",
    description="Foundation service for future scam-analysis and RAG capabilities.",
)

app.include_router(router)
