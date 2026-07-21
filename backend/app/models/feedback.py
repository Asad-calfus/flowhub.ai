from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Feedback(Base):
    """Raw feedback only - no generated analysis fields, so it can be reprocessed freely."""

    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # e.g. "FB-0001"
    feedback_text: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str | None] = mapped_column(String(50))
    feedback_created_at: Mapped[datetime | None] = mapped_column(DateTime)
    customer_id: Mapped[str | None] = mapped_column(String(30))
    customer_tier: Mapped[str | None] = mapped_column(String(20))
    product_version: Mapped[str | None] = mapped_column(String(20))
    rating: Mapped[int | None] = mapped_column(Integer)
    language: Mapped[str | None] = mapped_column(String(10))
    processing_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    analysis_results = relationship("AnalysisResult", back_populates="feedback", cascade="all, delete-orphan")
    embedding = relationship("Embedding", back_populates="feedback", cascade="all, delete-orphan", uselist=False)
    context_matches = relationship("ContextMatch", back_populates="feedback", cascade="all, delete-orphan")
    theme_memberships = relationship("ThemeMember", back_populates="feedback", cascade="all, delete-orphan")
