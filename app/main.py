"""FastAPI application entry point."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import router
from app.config import get_settings

# Validate configuration before the application accepts requests.
get_settings()

settings = get_settings()
app = FastAPI(
    title="Banteay Digital AI Service",
    version="0.1.0",
    description="Scam analysis and retrieval service.",
    docs_url=None if settings.environment == "production" else "/docs",
    redoc_url=None if settings.environment == "production" else "/redoc",
    openapi_url=None if settings.environment == "production" else "/openapi.json",
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_host_list)


@app.middleware("http")
async def reject_oversized_requests(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH"}:
        content_length = request.headers.get("content-length")
        if content_length is None:
            return JSONResponse(
                status_code=status.HTTP_411_LENGTH_REQUIRED,
                content={"detail": "Content-Length is required"},
            )
        try:
            length = int(content_length)
        except ValueError:
            length = settings.max_request_bytes + 1
        if length < 0 or length > settings.max_request_bytes:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "Request body is too large"},
            )
    return await call_next(request)

app.include_router(router)
