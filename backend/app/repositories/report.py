from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.report import Report


def create(db: Session, report: Report) -> Report:
    db.add(report)
    db.flush()
    return report


def get(db: Session, report_id: str) -> Optional[Report]:
    return db.get(Report, report_id)


def list_all(db: Session, page: int, page_size: int, workspace_id: str = "demo") -> tuple[list[Report], int]:
    base = select(Report).where(Report.workspace_id == workspace_id)
    total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
    stmt = base.order_by(Report.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = db.execute(stmt).scalars().all()
    return list(rows), total


def next_id(db: Session) -> str:
    last = db.execute(select(Report.id).order_by(Report.id.desc()).limit(1)).scalar_one_or_none()
    n = int(last.split("-")[1]) + 1 if last else 1
    return f"RPT-{n:04d}"
