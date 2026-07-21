from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from src.classification.schemas import CustomerTier, Source


class FeedbackCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feedback_text: str = Field(min_length=1)
    source: Optional[Source] = None
    feedback_created_at: Optional[datetime] = None
    customer_id: Optional[str] = None
    customer_tier: Optional[CustomerTier] = None
    product_version: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    language: Optional[str] = None


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    feedback_text: str
    source: Optional[str] = None
    feedback_created_at: Optional[datetime] = None
    customer_id: Optional[str] = None
    customer_tier: Optional[str] = None
    product_version: Optional[str] = None
    rating: Optional[int] = None
    language: Optional[str] = None
    processing_status: str
    created_at: datetime
    updated_at: datetime


class ImportSummary(BaseModel):
    feedback_imported: int = 0
    feedback_skipped: int = 0
    context_records_imported: int = 0
    context_records_skipped: int = 0
    analysis_results_imported: int = 0
    analysis_results_skipped: int = 0
    embeddings_imported: int = 0
    embeddings_skipped: int = 0
    context_matches_imported: int = 0
    context_matches_skipped: int = 0
    themes_imported: int = 0
    themes_skipped: int = 0
    theme_members_imported: int = 0
    theme_members_skipped: int = 0
    errors: list[str] = Field(default_factory=list)
