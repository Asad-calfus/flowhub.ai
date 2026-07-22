from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.correction import Correction


def create(db: Session, correction: Correction) -> Correction:
    db.add(correction)
    db.flush()
    return correction


def list_by_feedback_id(db: Session, feedback_id: str) -> list[Correction]:
    stmt = select(Correction).where(Correction.feedback_id == feedback_id).order_by(Correction.created_at.asc())
    return list(db.execute(stmt).scalars().all())


def counts_by_field(db: Session, workspace_id: str) -> dict[str, int]:
    stmt = (
        select(Correction.field, func.count(func.distinct(Correction.feedback_id)))
        .where(Correction.workspace_id == workspace_id)
        .group_by(Correction.field)
    )
    return {field: n for field, n in db.execute(stmt).all()}


def distinct_corrected_feedback_count(db: Session, workspace_id: str) -> int:
    stmt = select(func.count(func.distinct(Correction.feedback_id))).where(Correction.workspace_id == workspace_id)
    return db.execute(stmt).scalar_one()


def recent_examples(db: Session, workspace_id: str, limit: int = 50) -> list[Correction]:
    """Most recent corrections, newest first - used to build few-shot examples for the
    classifier so it stops repeating mistakes a human already fixed."""
    stmt = (
        select(Correction)
        .where(Correction.workspace_id == workspace_id)
        .order_by(Correction.created_at.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())
