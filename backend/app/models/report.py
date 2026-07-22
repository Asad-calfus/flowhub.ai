from datetime import datetime
from datetime import date as date_

from sqlalchemy import Boolean, Date, DateTime, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Report(Base):
    """One generated weekly report. Immutable once created - regenerating the same
    period produces a new row, same convention as `analysis_results`."""

    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # e.g. "RPT-0001"
    workspace_id: Mapped[str] = mapped_column(String(50), nullable=False, server_default="demo", index=True)
    start_date: Mapped[date_] = mapped_column(Date, nullable=False)
    end_date: Mapped[date_] = mapped_column(Date, nullable=False)
    is_all_time: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    product_module_filter: Mapped[str | None] = mapped_column(String(30))
    customer_tier_filter: Mapped[str | None] = mapped_column(String(20))

    generation_method: Mapped[str] = mapped_column(String(20), nullable=False)  # deterministic|dry_run|llm
    model_name: Mapped[str | None] = mapped_column(String(60))
    prompt_version: Mapped[str | None] = mapped_column(String(20))

    evidence_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    report_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    markdown: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
