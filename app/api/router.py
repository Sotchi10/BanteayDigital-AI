from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.retrieval import router as retrieval_router

router = APIRouter()
router.include_router(health_router)
router.include_router(retrieval_router)
