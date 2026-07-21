from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.schemas.analysis import (
    AnalysisOut,
    AnalysisRequest,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
)
from app.services import analysis_service

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/batch", response_model=BatchAnalysisResponse)
def run_batch_analysis(payload: BatchAnalysisRequest, db: Session = Depends(get_db)) -> BatchAnalysisResponse:
    results = analysis_service.run_batch(db, payload)
    db.commit()
    succeeded = sum(1 for r in results if r.status == "success")
    failed = sum(1 for r in results if r.status == "failed")
    skipped = sum(1 for r in results if r.status == "skipped")
    return BatchAnalysisResponse(requested=len(results), succeeded=succeeded, failed=failed, skipped=skipped, results=results)


@router.post("/{feedback_id}", response_model=AnalysisOut, status_code=status.HTTP_201_CREATED)
def analyze_feedback(feedback_id: str, payload: AnalysisRequest, db: Session = Depends(get_db)) -> AnalysisOut:
    result = analysis_service.analyze_feedback(db, feedback_id, payload)
    db.commit()
    return AnalysisOut.model_validate(result)


@router.get("/{feedback_id}", response_model=AnalysisOut)
def get_analysis(feedback_id: str, db: Session = Depends(get_db)) -> AnalysisOut:
    result = analysis_service.get_latest_analysis(db, feedback_id)
    if result is None:
        raise NotFoundError("AnalysisResult", feedback_id)
    return AnalysisOut.model_validate(result)
