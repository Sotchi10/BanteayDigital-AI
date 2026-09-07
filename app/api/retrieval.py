from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import require_service_key
from app.repositories.qdrant_store import QdrantStore
from app.schemas.retrieval import RetrieveRequest, RetrieveResponse, RetrievedMatch
from app.services.embedding_service import EmbeddingError, embed_text

router = APIRouter(prefix="/api/v1", tags=["retrieval"])


@router.post(
    "/retrieve",
    response_model=RetrieveResponse,
    dependencies=[Depends(require_service_key)],
)
def retrieve(request: RetrieveRequest) -> RetrieveResponse:
    """Find knowledge-base entries similar to the submitted scan input."""
    try:
        embedding = embed_text(request.value)
        store = QdrantStore()
        store.ensure_collection()
        points = store.search(embedding, limit=request.limit)
    except (EmbeddingError, RuntimeError, ValueError) as error:
        raise HTTPException(status_code=503, detail="Retrieval is unavailable") from error

    matches = [
        RetrievedMatch(
            id=str(point.id),
            score=point.score,
            payload=point.payload or {},
        )
        for point in points
    ]
    return RetrieveResponse(matches=matches)
