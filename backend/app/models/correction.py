from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Correction(Base):
    """A human correction to one classification field on one feedback record. Append-only
    audit trail - never updated or deleted. `analysis_service.correct_classification` also
    writes a new `AnalysisResult` row carrying the corrected value, so the correction is both
    recorded here (for the accuracy/few-shot feedback loop) and reflected in the live
    classification immediately."""

    __tablename__ = "corrections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[str] = mapped_column(String(50), nullable=False, server_default="demo", index=True)
    feedback_id: Mapped[str] = mapped_column(String(20), ForeignKey("feedback.id"), nullable=False, index=True)

    field: Mapped[str] = mapped_column(String(30), nullable=False)
    original_value: Mapped[str] = mapped_column(String(60), nullable=False)
    corrected_value: Mapped[str] = mapped_column(String(60), nullable=False)
    corrected_by: Mapped[str | None] = mapped_column(String(100))

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
