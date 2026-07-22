from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, model_validator

from src.reports.schemas import WeeklyReport

ReportGenerationMode = Literal["deterministic", "dry_run", "live"]


class ReportGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Both omitted (None) requests an all-time report over every feedback record in the
    # workspace, including records with no feedback_created_at at all.
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    mode: ReportGenerationMode = "deterministic"
    product_module: Optional[str] = None
    customer_tier: Optional[str] = None
    force: bool = False

    @model_validator(mode="after")
    def _dates_both_or_neither(self) -> "ReportGenerationRequest":
        if (self.start_date is None) != (self.end_date is None):
            raise ValueError("start_date and end_date must both be provided, or both omitted for an all-time report")
        return self


class ReportSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    start_date: date
    end_date: date
    is_all_time: bool = False
    product_module_filter: Optional[str] = None
    customer_tier_filter: Optional[str] = None
    generation_method: str
    model_name: Optional[str] = None
    prompt_version: Optional[str] = None
    created_at: datetime


class ReportOut(ReportSummaryOut):
    report: WeeklyReport
    markdown: str

    @classmethod
    def from_model(cls, row) -> "ReportOut":
        return cls(
            id=row.id,
            start_date=row.start_date,
            end_date=row.end_date,
            is_all_time=row.is_all_time,
            product_module_filter=row.product_module_filter,
            customer_tier_filter=row.customer_tier_filter,
            generation_method=row.generation_method,
            model_name=row.model_name,
            prompt_version=row.prompt_version,
            created_at=row.created_at,
            report=WeeklyReport(**row.report_json),
            markdown=row.markdown,
        )
