from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.classification.schemas import Category, FeedbackType, ProductModule, Sentiment, Urgency

AnalysisMethod = Literal["baseline", "llm"]


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: AnalysisMethod = "baseline"
    live: bool = False  # only meaningful when method="llm" - real API call, never automatic
    force: bool = False  # bypass the LLM cache and reclassify


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    feedback_id: str
    feedback_type: FeedbackType
    category: Category
    product_module: ProductModule
    sentiment: Sentiment
    urgency: Urgency
    confidence: float
    reasoning: str
    model_name: str
    prompt_version: Optional[str] = None
    created_at: datetime


class BatchAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feedback_ids: Optional[list[str]] = Field(
        default=None, description="Specific feedback IDs to analyze; omit to analyze all unprocessed feedback."
    )
    method: AnalysisMethod = "baseline"
    live: bool = False
    force: bool = False


class BatchAnalysisResultItem(BaseModel):
    feedback_id: str
    status: Literal["success", "failed", "skipped"]
    error: Optional[str] = None


class BatchAnalysisResponse(BaseModel):
    requested: int
    succeeded: int
    failed: int
    skipped: int
    results: list[BatchAnalysisResultItem]


class CostEstimateOut(BaseModel):
    """Pre-flight estimate for running live LLM classification over every pending
    (unclassified) feedback record in the workspace - never an actual spend."""

    pending_count: int
    provider: str
    model: str
    configured: bool  # whether an API key is set for `provider` - if false, a live run would 503
    estimated_cost_usd: Optional[float] = None
