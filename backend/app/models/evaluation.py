from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EvaluationRun(Base):
    """One run of the gold-set evaluation. Immutable once created - rerunning the
    evaluation produces a new row, same convention as `analysis_results`/`reports`."""

    __tablename__ = "evaluation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    model_name: Mapped[str] = mapped_column(String(60), nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False)
    scored_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_gold_count: Mapped[int] = mapped_column(Integer, nullable=False)
    metrics_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
