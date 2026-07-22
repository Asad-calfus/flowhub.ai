from datetime import datetime
from typing import Literal, Optional, get_args

from pydantic import BaseModel, ConfigDict, model_validator

from src.classification.schemas import Category, FeedbackType, ProductModule, Sentiment, Urgency

CorrectableField = Literal["feedback_type", "category", "product_module", "sentiment", "urgency"]

_FIELD_VALUES: dict[str, tuple] = {
    "feedback_type": get_args(FeedbackType),
    "category": get_args(Category),
    "product_module": get_args(ProductModule),
    "sentiment": get_args(Sentiment),
    "urgency": get_args(Urgency),
}


class CorrectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: CorrectableField
    corrected_value: str
    corrected_by: Optional[str] = None

    @model_validator(mode="after")
    def _value_matches_field(self) -> "CorrectionRequest":
        allowed = _FIELD_VALUES[self.field]
        if self.corrected_value not in allowed:
            raise ValueError(f"corrected_value for field '{self.field}' must be one of {allowed}")
        return self


class CorrectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    feedback_id: str
    field: str
    original_value: str
    corrected_value: str
    corrected_by: Optional[str] = None
    created_at: datetime


class CorrectionStatsOut(BaseModel):
    """Rule-based accuracy signal: what fraction of classified feedback has since received
    at least one human correction, overall and broken down by field. Not a substitute for
    a held-out eval set - just an operational signal that a category/module is drifting."""

    total_classified: int
    total_corrected_records: int
    correction_rate: float
    corrections_by_field: dict[str, int]
