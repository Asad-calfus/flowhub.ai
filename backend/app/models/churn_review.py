from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ChurnReview(Base):
    """Marks that a human has reviewed a customer's churn risk / suggested action - the
    score itself is always live-computed (src/churn/scoring.py), never stored; this table
    only tracks the human review step, one row per customer per workspace."""

    __tablename__ = "churn_reviews"
    __table_args__ = (UniqueConstraint("workspace_id", "customer_id", name="uq_churn_review_customer"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[str] = mapped_column(String(50), nullable=False, server_default="demo", index=True)
    customer_id: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(100))
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
