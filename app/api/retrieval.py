from threading import BoundedSemaphore

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import require_service_key
from app.config import get_settings
from app.repositories.qdrant_store import QdrantStore
from app.repositories.scam_case_repository import get_scam_case
from app.schemas.analysis import AnalyzeRequest, GroundedAnalysis
from app.schemas.retrieval import RetrieveRequest, RetrieveResponse, RetrievedMatch
from app.services.embedding_service import EmbeddingError, embed_query
from app.services.reasoning_service import ReasoningError, analyze_scan
from app.services.scam_case_indexer import index_scam_case

router = APIRouter(prefix="/api/v1", tags=["retrieval"])
_ai_slots = BoundedSemaphore(get_settings().ai_max_concurrency)


def _acquire_ai_slot() -> None:
    if not _ai_slots.acquire(blocking=False):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI service is busy; try again shortly",
        )


def build_retrieval_query(request: RetrieveRequest) -> str:
    """Keep query embeddings aligned with the labelled scam-case documents."""
    return f"Scan type: {request.type}\nContent: {request.value.strip()}"


@router.post(
    "/retrieve",
    response_model=RetrieveResponse,
    dependencies=[Depends(require_service_key)],
)
def retrieve(request: RetrieveRequest) -> RetrieveResponse:
    """Find knowledge-base entries similar to the submitted scan input."""
    _acquire_ai_slot()
    try:
        embedding = embed_query(build_retrieval_query(request))
        store = QdrantStore()
        store.ensure_collection()
        points = store.search(embedding, limit=request.limit)
    except (EmbeddingError, RuntimeError, ValueError) as error:
        raise HTTPException(status_code=503, detail="Retrieval is unavailable") from error
    finally:
        _ai_slots.release()

    matches = [
        RetrievedMatch(
            id=str(point.id),
            score=point.score,
            payload=point.payload or {},
        )
        for point in points
    ]
    return RetrieveResponse(matches=matches)


@router.post(
    "/analyze",
    response_model=GroundedAnalysis,
    dependencies=[Depends(require_service_key)],
)
def analyze(request: AnalyzeRequest) -> GroundedAnalysis:
    """Generate a grounded explanation from scan evidence supplied by the backend."""
    _acquire_ai_slot()
    try:
        return analyze_scan(request)
    except ReasoningError as error:
        raise HTTPException(status_code=503, detail="Grounded analysis is unavailable") from error
    finally:
        _ai_slots.release()


@router.post(
    "/index/scam-cases/{case_id}",
    dependencies=[Depends(require_service_key)],
)
def index_case(case_id: int) -> dict[str, int]:
    """Re-index one admin-managed ScamCase after it changes in MySQL."""
    settings = get_settings()
    if not settings.database_url:
        raise HTTPException(status_code=503, detail="Database indexing is not configured")

    _acquire_ai_slot()
    try:
        scam_case = get_scam_case(settings.database_url, case_id)
        store = QdrantStore()
        store.ensure_collection()
        index_scam_case(scam_case, store)
    except (LookupError, RuntimeError, ValueError) as error:
        raise HTTPException(status_code=503, detail="Scam-case indexing is unavailable") from error
    finally:
        _ai_slots.release()

    return {"caseId": case_id}
