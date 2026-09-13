from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.dependencies import require_service_key
from app.config import get_settings
from app.schemas.ocr import OcrResponse
from app.services.ocr_service import OcrError, extract_text

router = APIRouter(prefix="/api/v1", tags=["ocr"])


@router.post(
    "/ocr",
    response_model=OcrResponse,
    dependencies=[Depends(require_service_key)],
)
async def ocr_image(image: UploadFile = File(...)) -> OcrResponse:
    """Extract visible text from a scan screenshot or photo."""
    if image.content_type and not image.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload an image file")

    image_bytes = await image.read()
    settings = get_settings()
    try:
        text = extract_text(image_bytes, settings)
    except OcrError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    finally:
        await image.close()

    return OcrResponse(text=text, languages=settings.ocr_languages, character_count=len(text))
