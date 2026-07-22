from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.workspace import get_workspace_id
from app.schemas.common import Page
from app.schemas.report import ReportGenerationRequest, ReportOut, ReportShareLinkOut, ReportSummaryOut
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/weekly", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def generate_weekly_report(
    payload: ReportGenerationRequest, db: Session = Depends(get_db), workspace_id: str = Depends(get_workspace_id)
) -> ReportOut:
    report = report_service.generate_report(db, payload, workspace_id)
    db.commit()
    return ReportOut.from_model(report)


@router.get("", response_model=Page[ReportSummaryOut])
def list_reports(
    db: Session = Depends(get_db),
    workspace_id: str = Depends(get_workspace_id),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
) -> Page[ReportSummaryOut]:
    items, total = report_service.list_reports(db, page, page_size, workspace_id)
    return Page(items=[ReportSummaryOut.model_validate(i) for i in items], total=total, page=page, page_size=page_size)


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: str, db: Session = Depends(get_db)) -> ReportOut:
    report = report_service.get_report(db, report_id)
    return ReportOut.from_model(report)


@router.get("/{report_id}/pdf")
def download_report_pdf(report_id: str, token: str | None = Query(default=None), db: Session = Depends(get_db)) -> Response:
    pdf_bytes = report_service.render_report_pdf(db, report_id, token)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{report_id}.pdf"'},
    )


@router.post("/{report_id}/share", response_model=ReportShareLinkOut)
def create_report_share_link(report_id: str, db: Session = Depends(get_db)) -> ReportShareLinkOut:
    token, expires_at = report_service.create_share_link(db, report_id)
    return ReportShareLinkOut(
        report_id=report_id,
        token=token,
        path=f"{settings.API_V1_PREFIX}/reports/{report_id}/pdf?token={token}",
        expires_at=datetime.fromtimestamp(expires_at, tz=timezone.utc),
    )
