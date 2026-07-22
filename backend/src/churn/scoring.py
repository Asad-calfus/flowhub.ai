"""Rule-based, deterministic churn risk scoring - no LLM, no ML model. Every number is
derived directly from stored feedback/analysis data so the score is always explainable,
same philosophy as `src.reports.aggregator` (deterministic first, LLM only for wording).

Score = weighted blend of three signals, each in [0, 1]:
  - negative_ratio: share of this customer's feedback with Negative sentiment
  - high_urgency_ratio: share flagged High urgency
  - recent_negative: 1.0 if their most recent feedback was Negative, else 0.0
      (a customer whose *latest* interaction was negative is a stronger churn signal
      than one whose negativity is old news, even at the same overall ratio)
"""

from dataclasses import dataclass
from typing import Literal

RiskLevel = Literal["Low", "Medium", "High"]

NEGATIVE_RATIO_WEIGHT = 0.5
HIGH_URGENCY_WEIGHT = 0.3
RECENT_NEGATIVE_WEIGHT = 0.2

HIGH_RISK_THRESHOLD = 70
MEDIUM_RISK_THRESHOLD = 40


@dataclass
class CustomerRiskInputs:
    customer_id: str
    customer_tier: str | None
    total_feedback: int
    negative_count: int
    high_urgency_count: int
    last_feedback_sentiment: str | None


@dataclass
class CustomerRiskScore:
    customer_id: str
    customer_tier: str | None
    risk_score: int
    risk_level: RiskLevel
    total_feedback: int
    negative_count: int
    high_urgency_count: int
    last_feedback_sentiment: str | None
    suggested_action: str
    reviewed: bool = False  # filled in by app/services/churn_service.py, not scoring logic


def _risk_level(score: int) -> RiskLevel:
    if score >= HIGH_RISK_THRESHOLD:
        return "High"
    if score >= MEDIUM_RISK_THRESHOLD:
        return "Medium"
    return "Low"


def _suggested_action(risk_level: RiskLevel, customer_tier: str | None) -> str:
    """Rule-based only, same "no LLM" stance as the score itself - a human still reviews
    and marks it handled (see ChurnReview) before anything is considered done."""
    if risk_level == "High":
        return "Escalate to account manager immediately" if customer_tier == "Enterprise" else "Reach out proactively"
    if risk_level == "Medium":
        return "Monitor and follow up"
    return "No action needed"


def score_customer(inputs: CustomerRiskInputs) -> CustomerRiskScore:
    if inputs.total_feedback == 0:
        risk_score = 0
    else:
        negative_ratio = inputs.negative_count / inputs.total_feedback
        high_urgency_ratio = inputs.high_urgency_count / inputs.total_feedback
        recent_negative = 1.0 if inputs.last_feedback_sentiment == "Negative" else 0.0
        blended = (
            NEGATIVE_RATIO_WEIGHT * negative_ratio
            + HIGH_URGENCY_WEIGHT * high_urgency_ratio
            + RECENT_NEGATIVE_WEIGHT * recent_negative
        )
        risk_score = round(min(1.0, blended) * 100)

    risk_level = _risk_level(risk_score)
    return CustomerRiskScore(
        customer_id=inputs.customer_id,
        customer_tier=inputs.customer_tier,
        risk_score=risk_score,
        risk_level=risk_level,
        total_feedback=inputs.total_feedback,
        negative_count=inputs.negative_count,
        high_urgency_count=inputs.high_urgency_count,
        last_feedback_sentiment=inputs.last_feedback_sentiment,
        suggested_action=_suggested_action(risk_level, inputs.customer_tier),
    )
