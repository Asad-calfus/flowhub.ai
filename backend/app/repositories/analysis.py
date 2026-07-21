from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisResult


def create(db: Session, result: AnalysisResult) -> AnalysisResult:
    db.add(result)
    db.flush()
    return result


def get_latest(db: Session, feedback_id: str) -> Optional[AnalysisResult]:
    stmt = (
        select(AnalysisResult)
        .where(AnalysisResult.feedback_id == feedback_id)
        .order_by(AnalysisResult.created_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalars().first()


def list_by_feedback_ids(db: Session, feedback_ids: list[str]) -> dict[str, AnalysisResult]:
    """Latest analysis result per feedback_id, for the given ids."""
    if not feedback_ids:
        return {}
    stmt = select(AnalysisResult).where(AnalysisResult.feedback_id.in_(feedback_ids)).order_by(
        AnalysisResult.created_at.desc()
    )
    latest: dict[str, AnalysisResult] = {}
    for row in db.execute(stmt).scalars().all():
        latest.setdefault(row.feedback_id, row)
    return latest
