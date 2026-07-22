from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Theme(Base):
    __tablename__ = "themes"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # e.g. "THM-001"
    workspace_id: Mapped[str] = mapped_column(String(50), nullable=False, server_default="demo", index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    keywords: Mapped[list | None] = mapped_column(JSON)
    feedback_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_seen: Mapped[date | None] = mapped_column(Date)
    last_seen: Mapped[date | None] = mapped_column(Date)
    trend_status: Mapped[str | None] = mapped_column(String(20))  # new|growing|stable|declining

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    members = relationship("ThemeMember", back_populates="theme", cascade="all, delete-orphan")


class ThemeMember(Base):
    __tablename__ = "theme_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    theme_id: Mapped[str] = mapped_column(String(20), ForeignKey("themes.id"), nullable=False)
    feedback_id: Mapped[str] = mapped_column(String(20), ForeignKey("feedback.id"), nullable=False)
    membership_score: Mapped[float | None] = mapped_column(Float)

    theme = relationship("Theme", back_populates="members")
    feedback = relationship("Feedback", back_populates="theme_memberships")
