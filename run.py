"""Run the AI service using the environment-backed application settings."""

import json
import socket
from urllib.error import URLError
from urllib.request import urlopen

import uvicorn

from app.config import get_settings


def probe_host(configured_host: str) -> str:
    """Return a local address suitable for checking a wildcard listener."""
    return "127.0.0.1" if configured_host in {"0.0.0.0", "::"} else configured_host


def service_is_running(host: str, port: int) -> bool:
    """Check whether this AI service is already healthy on the configured port."""
    try:
        with urlopen(f"http://{probe_host(host)}:{port}/health", timeout=2) as response:
            payload = json.load(response)
        return payload.get("status") == "ok" and payload.get("service") == "banteay-ai-service"
    except (OSError, URLError, ValueError, json.JSONDecodeError):
        return False


def port_is_available(host: str, port: int) -> bool:
    """Check for a conflicting or Windows-reserved listening port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind((host, port))
        return True
    except OSError:
        return False


def main() -> None:
    """Start Uvicorn with the host and port configured for this service."""
    settings = get_settings()
    if service_is_running(settings.host, settings.port):
        print(
            f"Banteay Digital AI service is already running at "
            f"http://{probe_host(settings.host)}:{settings.port}"
        )
        return
    if not port_is_available(settings.host, settings.port):
        raise SystemExit(
            f"Cannot start the AI service: {settings.host}:{settings.port} is already "
            "in use or reserved by Windows. Stop the conflicting process or set a "
            "different PORT in the AI service configuration."
        )
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
    )


if __name__ == "__main__":
    main()
