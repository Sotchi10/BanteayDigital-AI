import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import require_service_key
from app.config import get_settings
from app.schemas.ocr import OcrResponse
from app.services.ocr_service import OcrError, extract_text

router = APIRouter(prefix="/api/v1", tags=["ocr"])
_ocr_semaphore: asyncio.Semaphore | None = None


def _get_ocr_semaphore() -> asyncio.Semaphore:
    global _ocr_semaphore
    if _ocr_semaphore is None:
        _ocr_semaphore = asyncio.Semaphore(get_settings().ocr_max_concurrency)
    return _ocr_semaphore


async def _read_limited(image: UploadFile, maximum_bytes: int) -> bytes:
    data = await image.read(maximum_bytes + 1)
    if len(data) > maximum_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The uploaded image exceeds the OCR size limit",
        )
    return data


@router.post(
    "/ocr",
    response_model=OcrResponse,
    dependencies=[Depends(require_service_key)],
)
async def ocr_image(image: UploadFile = File(...)) -> OcrResponse:
    """Extract visible text from a scan screenshot or photo."""
    if image.content_type and not image.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload an image file")

    settings = get_settings()
    try:
        image_bytes = await _read_limited(image, settings.ocr_max_image_bytes)
        async with _get_ocr_semaphore():
            text = await run_in_threadpool(extract_text, image_bytes, settings)
    except OcrError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    finally:
        await image.close()

    return OcrResponse(text=text, languages=settings.ocr_languages, character_count=len(text))
