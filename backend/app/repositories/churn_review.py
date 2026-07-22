from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from app.models.churn_review import ChurnReview


def reviewed_customer_ids(db: Session, workspace_id: str) -> set[str]:
    stmt = select(ChurnReview.customer_id).where(ChurnReview.workspace_id == workspace_id)
    return set(db.execute(stmt).scalars().all())


def mark_reviewed(db: Session, workspace_id: str, customer_id: str, reviewed_by: str | None) -> ChurnReview:
    """Upsert - re-marking an already-reviewed customer just refreshes reviewed_by/at
    rather than erroring on the unique constraint."""
    stmt = (
        insert(ChurnReview)
        .values(workspace_id=workspace_id, customer_id=customer_id, reviewed_by=reviewed_by)
        .on_conflict_do_update(
            index_elements=["workspace_id", "customer_id"],
            set_={"reviewed_by": reviewed_by, "reviewed_at": func.now()},
        )
        .returning(ChurnReview)
    )
    row = db.execute(stmt).scalar_one()
    db.flush()
    return row
