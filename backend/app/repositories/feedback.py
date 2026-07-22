from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.feedback import Feedback


def get(db: Session, feedback_id: str) -> Optional[Feedback]:
    return db.get(Feedback, feedback_id)


def exists(db: Session, feedback_id: str) -> bool:
    return get(db, feedback_id) is not None


def create(db: Session, feedback: Feedback) -> Feedback:
    db.add(feedback)
    db.flush()
    return feedback


def delete(db: Session, feedback: Feedback) -> None:
    db.delete(feedback)
    db.flush()


def get_many(db: Session, feedback_ids: list[str]) -> dict[str, Feedback]:
    if not feedback_ids:
        return {}
    stmt = select(Feedback).where(Feedback.id.in_(feedback_ids))
    return {f.id: f for f in db.execute(stmt).scalars().all()}


def list_ids_by_status(db: Session, processing_status: str, workspace_id: str = "demo") -> list[str]:
    stmt = (
        select(Feedback.id)
        .where(Feedback.processing_status == processing_status, Feedback.workspace_id == workspace_id)
        .order_by(Feedback.id)
    )
    return list(db.execute(stmt).scalars().all())


def next_id(db: Session) -> str:
    """Generate the next sequential FB-#### id."""
    last = db.execute(select(Feedback.id).order_by(Feedback.id.desc()).limit(1)).scalar_one_or_none()
    n = int(last.split("-")[1]) + 1 if last else 1
    return f"FB-{n:04d}"


def list_filtered(
    db: Session,
    *,
    page: int,
    page_size: int,
    workspace_id: str = "demo",
    source: Optional[str] = None,
    sentiment: Optional[str] = None,
    category: Optional[str] = None,
    product_module: Optional[str] = None,
    customer_tier: Optional[str] = None,
    processing_status: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> tuple[list[Feedback], int]:
    from app.models.analysis import AnalysisResult

    query = select(Feedback).where(Feedback.workspace_id == workspace_id)
    needs_analysis_join = any([sentiment, category, product_module])
    if needs_analysis_join:
        query = query.join(AnalysisResult, AnalysisResult.feedback_id == Feedback.id)
        if sentiment:
            query = query.where(AnalysisResult.sentiment == sentiment)
        if category:
            query = query.where(AnalysisResult.category == category)
        if product_module:
            query = query.where(AnalysisResult.product_module == product_module)

    if source:
        query = query.where(Feedback.source == source)
    if customer_tier:
        query = query.where(Feedback.customer_tier == customer_tier)
    if processing_status:
        query = query.where(Feedback.processing_status == processing_status)
    if date_from:
        query = query.where(Feedback.feedback_created_at >= date_from)
    if date_to:
        query = query.where(Feedback.feedback_created_at <= date_to)

    query = query.distinct().order_by(Feedback.id)

    total = len(db.execute(query).all())
    rows = db.execute(query.offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return list(rows), total
