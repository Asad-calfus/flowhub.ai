from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.context import ContextMatch, ContextRecord


def get_record(db: Session, context_id: str) -> Optional[ContextRecord]:
    return db.get(ContextRecord, context_id)


def upsert_record(db: Session, record: ContextRecord) -> tuple[ContextRecord, bool]:
    """Returns (record, created)."""
    existing = get_record(db, record.id)
    if existing:
        return existing, False
    db.add(record)
    db.flush()
    return record, True


def list_records_by_type(db: Session, context_type: str) -> list[ContextRecord]:
    stmt = select(ContextRecord).where(ContextRecord.context_type == context_type)
    return list(db.execute(stmt).scalars().all())


def create_match(db: Session, match: ContextMatch) -> ContextMatch:
    db.add(match)
    db.flush()
    return match


def list_matches_for_feedback(db: Session, feedback_id: str) -> list[ContextMatch]:
    stmt = select(ContextMatch).where(ContextMatch.feedback_id == feedback_id).order_by(
        ContextMatch.match_type, ContextMatch.rank
    )
    return list(db.execute(stmt).scalars().all())


def delete_matches_for_feedback(db: Session, feedback_id: str) -> None:
    for m in list_matches_for_feedback(db, feedback_id):
        db.delete(m)
    db.flush()


def list_feedback_ids_without_matches(db: Session, workspace_id: str = "demo") -> list[str]:
    """Feedback ids in the workspace with zero ContextMatch rows - i.e. retrieval has never
    run for them (see aggregator._new_untracked_feedback_ids's "unprocessed" bucket, which
    this same "no rows at all" check drives)."""
    from app.models.feedback import Feedback

    already_matched = select(ContextMatch.feedback_id).distinct()
    stmt = (
        select(Feedback.id)
        .where(Feedback.workspace_id == workspace_id, Feedback.id.notin_(already_matched))
        .order_by(Feedback.id)
    )
    return list(db.execute(stmt).scalars().all())
