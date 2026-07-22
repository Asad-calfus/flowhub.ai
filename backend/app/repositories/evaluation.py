from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.evaluation import EvaluationRun


def create(db: Session, run: EvaluationRun) -> EvaluationRun:
    db.add(run)
    db.flush()
    return run


def get(db: Session, run_id: int) -> Optional[EvaluationRun]:
    return db.get(EvaluationRun, run_id)


def list_all(db: Session, page: int, page_size: int) -> tuple[list[EvaluationRun], int]:
    total = db.execute(select(func.count()).select_from(EvaluationRun)).scalar_one()
    stmt = (
        select(EvaluationRun)
        .order_by(EvaluationRun.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = db.execute(stmt).scalars().all()
    return list(rows), total


def get_latest(db: Session, model_name: Optional[str] = None) -> Optional[EvaluationRun]:
    stmt = select(EvaluationRun).order_by(EvaluationRun.created_at.desc())
    if model_name is not None:
        stmt = stmt.where(EvaluationRun.model_name == model_name)
    return db.execute(stmt.limit(1)).scalars().first()
