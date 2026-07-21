from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.embedding import EMBEDDING_DIM


class ContextRecord(Base):
    """Unified store for known bugs, feature requests, releases, and product modules."""

    __tablename__ = "context_records"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # e.g. "BUG-001", "FR-001", "v2.4.0", "MOD-01"
    context_type: Mapped[str] = mapped_column(String(20), nullable=False)  # known_bug|feature_request|release|product_module
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String)
    product_module: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str | None] = mapped_column(String(30))
    version_metadata: Mapped[dict | None] = mapped_column(JSON)
    vector: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    raw_metadata: Mapped[dict | None] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    matches = relationship("ContextMatch", back_populates="context_record", cascade="all, delete-orphan")


class ContextMatch(Base):
    """One candidate pairing between a feedback record and a context record."""

    __tablename__ = "context_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    feedback_id: Mapped[str] = mapped_column(String(20), ForeignKey("feedback.id"), nullable=False)
    context_record_id: Mapped[str] = mapped_column(String(20), ForeignKey("context_records.id"), nullable=False)

    match_type: Mapped[str] = mapped_column(String(20), nullable=False)  # known_bug|feature_request|release
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    match_status: Mapped[str] = mapped_column(String(30), nullable=False)  # matched|candidate

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    feedback = relationship("Feedback", back_populates="context_matches")
    context_record = relationship("ContextRecord", back_populates="matches")
