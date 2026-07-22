from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.workspace import get_workspace_id
from app.schemas.analysis import (
    AnalysisOut,
    AnalysisRequest,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    CostEstimateOut,
)
from app.schemas.correction import CorrectionOut, CorrectionRequest, CorrectionStatsOut
from app.services import analysis_service

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/estimate", response_model=CostEstimateOut)
def estimate_batch_cost(
    db: Session = Depends(get_db), workspace_id: str = Depends(get_workspace_id)
) -> CostEstimateOut:
    return analysis_service.estimate_batch_cost(db, workspace_id)


@router.post("/batch", response_model=BatchAnalysisResponse)
def run_batch_analysis(
    payload: BatchAnalysisRequest, db: Session = Depends(get_db), workspace_id: str = Depends(get_workspace_id)
) -> BatchAnalysisResponse:
    results = analysis_service.run_batch(db, payload, workspace_id)
    db.commit()
    succeeded = sum(1 for r in results if r.status == "success")
    failed = sum(1 for r in results if r.status == "failed")
    skipped = sum(1 for r in results if r.status == "skipped")
    return BatchAnalysisResponse(requested=len(results), succeeded=succeeded, failed=failed, skipped=skipped, results=results)


@router.get("/corrections/stats", response_model=CorrectionStatsOut)
def correction_stats(db: Session = Depends(get_db), workspace_id: str = Depends(get_workspace_id)) -> CorrectionStatsOut:
    return analysis_service.get_correction_stats(db, workspace_id)


@router.post("/{feedback_id}", response_model=AnalysisOut, status_code=status.HTTP_201_CREATED)
def analyze_feedback(
    feedback_id: str, payload: AnalysisRequest, db: Session = Depends(get_db), workspace_id: str = Depends(get_workspace_id)
) -> AnalysisOut:
    result = analysis_service.analyze_feedback(db, feedback_id, payload, workspace_id)
    db.commit()
    return AnalysisOut.model_validate(result)


@router.get("/{feedback_id}", response_model=AnalysisOut)
def get_analysis(feedback_id: str, db: Session = Depends(get_db)) -> AnalysisOut:
    result = analysis_service.get_latest_analysis(db, feedback_id)
    if result is None:
        raise NotFoundError("AnalysisResult", feedback_id)
    return AnalysisOut.model_validate(result)


@router.patch("/{feedback_id}/classification", response_model=AnalysisOut)
def correct_classification(
    feedback_id: str, payload: CorrectionRequest, db: Session = Depends(get_db), workspace_id: str = Depends(get_workspace_id)
) -> AnalysisOut:
    analysis_service.correct_classification(db, feedback_id, payload, workspace_id)
    db.commit()
    return AnalysisOut.model_validate(analysis_service.get_latest_analysis(db, feedback_id))


@router.get("/{feedback_id}/corrections", response_model=list[CorrectionOut])
def list_corrections(feedback_id: str, db: Session = Depends(get_db)) -> list[CorrectionOut]:
    corrections = analysis_service.list_corrections(db, feedback_id)
    return [CorrectionOut.model_validate(c) for c in corrections]
