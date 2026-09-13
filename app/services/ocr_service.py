"""Tesseract-backed OCR with explicit runtime configuration."""

from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError
import pytesseract
from pytesseract import TesseractError, TesseractNotFoundError

from app.config import Settings


class OcrError(RuntimeError):
    """An OCR request could not be processed safely."""


def _configure_tesseract(settings: Settings) -> None:
    if settings.tesseract_cmd:
        executable = Path(settings.tesseract_cmd)
        if not executable.is_file():
            raise OcrError("Tesseract executable is not available")
        pytesseract.pytesseract.tesseract_cmd = str(executable)


def _tessdata_config(settings: Settings) -> str:
    if not settings.ocr_tessdata_dir:
        return ""
    tessdata_dir = Path(settings.ocr_tessdata_dir)
    if not tessdata_dir.is_dir():
        raise OcrError("The configured Tesseract language-data directory is not available")
    # pytesseract's Windows argument parsing preserves quote characters. The
    # project-local default has no spaces and is therefore passed verbatim.
    # Use TESSDATA_PREFIX externally for a language-data path containing spaces.
    if " " in str(tessdata_dir):
        raise OcrError("OCR_TESSDATA_DIR cannot contain spaces on Windows; use TESSDATA_PREFIX instead")
    return f"--tessdata-dir {tessdata_dir}"


def extract_text(image_bytes: bytes, settings: Settings) -> str:
    """Extract text without persisting the uploaded image to disk."""
    if not image_bytes:
        raise OcrError("The uploaded image is empty")
    if len(image_bytes) > settings.ocr_max_image_bytes:
        raise OcrError("The uploaded image exceeds the OCR size limit")

    _configure_tesseract(settings)
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image.load()
            return pytesseract.image_to_string(
                image,
                lang=settings.ocr_languages,
                config=_tessdata_config(settings),
                timeout=settings.ocr_timeout_seconds,
            ).strip()
    except (UnidentifiedImageError, OSError) as error:
        raise OcrError("The upload is not a readable image") from error
    except TesseractNotFoundError as error:
        raise OcrError("Tesseract executable is not available") from error
    except (TesseractError, RuntimeError) as error:
        raise OcrError("OCR is unavailable; check the configured OCR languages") from error
