from typing import Optional

from pydantic import BaseModel, ConfigDict

from src.churn.scoring import RiskLevel


class CustomerRiskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_id: str
    customer_tier: Optional[str] = None
    risk_score: int
    risk_level: RiskLevel
    total_feedback: int
    negative_count: int
    high_urgency_count: int
    last_feedback_sentiment: Optional[str] = None
    suggested_action: str
    reviewed: bool = False


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewed_by: Optional[str] = None
