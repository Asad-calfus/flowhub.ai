from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.workspace import get_workspace_id
from app.schemas.common import Page
from app.schemas.feedback import FeedbackCreate, FeedbackOut, ImportSummary
from app.schemas.retrieval import ContextMatchSummary, RetrievalBatchRequest, RetrievalBatchResponse, SimilarFeedbackOut
from app.services import feedback_service, retrieval_service

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
def create_feedback(
    payload: FeedbackCreate, db: Session = Depends(get_db), workspace_id: str = Depends(get_workspace_id)
) -> FeedbackOut:
    feedback = feedback_service.create_feedback(db, payload, workspace_id)
    db.commit()
    return FeedbackOut.model_validate(feedback)


@router.post("/import", response_model=ImportSummary)
async def import_feedback(
    file: UploadFile, db: Session = Depends(get_db), workspace_id: str = Depends(get_workspace_id)
) -> ImportSummary:
    content = await file.read()
    summary = feedback_service.import_feedback_csv(db, content, workspace_id)
    db.commit()
    return summary


@router.post("/retrieval/batch", response_model=RetrievalBatchResponse)
def run_batch_retrieval(
    payload: RetrievalBatchRequest, db: Session = Depends(get_db), workspace_id: str = Depends(get_workspace_id)
) -> RetrievalBatchResponse:
    results = retrieval_service.run_batch(db, payload, workspace_id)
    db.commit()
    succeeded = sum(1 for r in results if r.status == "success")
    failed = sum(1 for r in results if r.status == "failed")
    return RetrievalBatchResponse(requested=len(results), succeeded=succeeded, failed=failed, results=results)


@router.get("", response_model=Page[FeedbackOut])
def list_feedback(
    db: Session = Depends(get_db),
    workspace_id: str = Depends(get_workspace_id),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
    source: Optional[str] = None,
    sentiment: Optional[str] = None,
    category: Optional[str] = None,
    product_module: Optional[str] = None,
    customer_tier: Optional[str] = None,
    customer_id: Optional[str] = None,
    processing_status: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> Page[FeedbackOut]:
    items, total = feedback_service.list_feedback(
        db,
        workspace_id=workspace_id,
        page=page,
        page_size=page_size,
        source=source,
        sentiment=sentiment,
        category=category,
        product_module=product_module,
        customer_tier=customer_tier,
        customer_id=customer_id,
        processing_status=processing_status,
        date_from=date_from,
        date_to=date_to,
    )
    return Page(items=[FeedbackOut.model_validate(i) for i in items], total=total, page=page, page_size=page_size)


@router.get("/{feedback_id}", response_model=FeedbackOut)
def get_feedback(feedback_id: str, db: Session = Depends(get_db)) -> FeedbackOut:
    return FeedbackOut.model_validate(feedback_service.get_feedback(db, feedback_id))


@router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_feedback(feedback_id: str, db: Session = Depends(get_db)) -> None:
    feedback_service.delete_feedback(db, feedback_id)
    db.commit()


@router.get("/{feedback_id}/similar", response_model=list[SimilarFeedbackOut])
def get_similar_feedback(
    feedback_id: str,
    db: Session = Depends(get_db),
    top_k: int = Query(default=settings.DEFAULT_TOP_K, ge=1, le=settings.MAX_TOP_K),
) -> list[SimilarFeedbackOut]:
    results = retrieval_service.get_similar_feedback(db, feedback_id, top_k)
    db.commit()
    return results


@router.get("/{feedback_id}/context-matches", response_model=ContextMatchSummary)
def get_context_matches(
    feedback_id: str,
    db: Session = Depends(get_db),
    top_k: int = Query(default=settings.DEFAULT_TOP_K, ge=1, le=settings.MAX_TOP_K),
) -> ContextMatchSummary:
    result = retrieval_service.get_context_matches(db, feedback_id, top_k)
    db.commit()
    return result
