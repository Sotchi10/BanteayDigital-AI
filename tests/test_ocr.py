from fastapi.testclient import TestClient

from app.api import ocr
from app.config import get_settings
from app.main import app
from app.services import ocr_service


def test_ocr_extracts_uploaded_image_text(monkeypatch) -> None:
    # Keep the test independent of local .env language settings.
    settings = get_settings().model_copy(update={"ocr_languages": "khm+eng"})
    monkeypatch.setattr(ocr, "get_settings", lambda: settings)
    monkeypatch.setattr(ocr, "extract_text", lambda image_bytes, settings: "លេខកូដ OTP")
    configured_key = get_settings().ai_service_api_key
    headers = {"X-AI-Service-Key": configured_key.get_secret_value()} if configured_key else {}

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/ocr",
            headers=headers,
            files={"image": ("scan.png", b"not-used-by-mock", "image/png")},
        )

    assert response.status_code == 200
    assert response.json() == {
        "text": "លេខកូដ OTP",
        "languages": "khm+eng",
        "character_count": 10,
    }


def test_ocr_rejects_non_image_upload() -> None:
    configured_key = get_settings().ai_service_api_key
    headers = {"X-AI-Service-Key": configured_key.get_secret_value()} if configured_key else {}
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/ocr",
            headers=headers,
            files={"image": ("scan.txt", b"text", "text/plain")},
        )

    assert response.status_code == 415


def test_ocr_discovers_tesseract_and_uses_installed_english(monkeypatch) -> None:
    settings = get_settings().model_copy(
        update={"tesseract_cmd": None, "ocr_languages": "eng", "ocr_tessdata_dir": ".missing-test-tessdata"}
    )
    monkeypatch.setattr(ocr_service.shutil, "which", lambda command: "C:/Tesseract/tesseract.exe")
    monkeypatch.setattr(ocr_service.pytesseract, "get_languages", lambda config: ["eng", "osd"])
    monkeypatch.setattr(ocr_service.pytesseract, "image_to_string", lambda image, lang, config, timeout: "Suspicious message")
    monkeypatch.setattr(ocr_service.Image, "open", lambda _stream: _FakeImage())

    assert ocr_service.extract_text(b"image-bytes", settings) == "Suspicious message"


class _FakeImage:
    size = (100, 100)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def load(self):
        return None
