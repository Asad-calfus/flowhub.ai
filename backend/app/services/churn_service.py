"""Churn risk service - raw SQL aggregation (GROUP BY, window function) per the project's
SQLAlchemy-for-CRUD/text()-for-aggregations convention. Scoring itself lives in
src/churn/scoring.py, kept deterministic and separate from the query.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.churn.scoring import CustomerRiskInputs, CustomerRiskScore, score_customer

_CUSTOMER_FEEDBACK_SQL = """
    WITH latest_analysis AS (
        SELECT DISTINCT ON (feedback_id) feedback_id, sentiment, urgency
        FROM analysis_results
        ORDER BY feedback_id, created_at DESC
    ),
    customer_latest AS (
        SELECT DISTINCT ON (f.customer_id) f.customer_id, la.sentiment AS last_sentiment
        FROM feedback f
        LEFT JOIN latest_analysis la ON la.feedback_id = f.id
        WHERE f.workspace_id = :workspace_id AND f.customer_id IS NOT NULL
        ORDER BY f.customer_id, f.feedback_created_at DESC NULLS LAST
    )
    SELECT
        f.customer_id,
        MAX(f.customer_tier) AS customer_tier,
        COUNT(*) AS total_feedback,
        COUNT(*) FILTER (WHERE la.sentiment = 'Negative') AS negative_count,
        COUNT(*) FILTER (WHERE la.urgency = 'High') AS high_urgency_count,
        MAX(cl.last_sentiment) AS last_feedback_sentiment
    FROM feedback f
    LEFT JOIN latest_analysis la ON la.feedback_id = f.id
    LEFT JOIN customer_latest cl ON cl.customer_id = f.customer_id
    WHERE f.workspace_id = :workspace_id AND f.customer_id IS NOT NULL
    GROUP BY f.customer_id
"""


def _all_customer_scores(db: Session, workspace_id: str) -> list[CustomerRiskScore]:
    rows = db.execute(text(_CUSTOMER_FEEDBACK_SQL), {"workspace_id": workspace_id}).all()
    scores = [
        score_customer(
            CustomerRiskInputs(
                customer_id=row.customer_id,
                customer_tier=row.customer_tier,
                total_feedback=row.total_feedback,
                negative_count=row.negative_count,
                high_urgency_count=row.high_urgency_count,
                last_feedback_sentiment=row.last_feedback_sentiment,
            )
        )
        for row in rows
    ]
    scores.sort(key=lambda s: -s.risk_score)
    return scores


def list_at_risk_customers(db: Session, workspace_id: str = "demo", limit: int = 20) -> list[CustomerRiskScore]:
    return _all_customer_scores(db, workspace_id)[:limit]


def get_customer_risk(db: Session, customer_id: str, workspace_id: str = "demo") -> CustomerRiskScore | None:
    return next((s for s in _all_customer_scores(db, workspace_id) if s.customer_id == customer_id), None)
