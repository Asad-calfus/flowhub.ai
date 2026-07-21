from typing import Optional

from pydantic import BaseModel, ConfigDict

from src.retrieval.schemas import ContextStatus, ContextType


class SimilarFeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    feedback_id: str
    matched_feedback_id: str
    rank: int
    similarity_score: float
    text_preview: str


class ContextMatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    feedback_id: str
    context_record_id: str
    context_type: ContextType
    title: str
    match_type: str
    similarity_score: float
    rank: int
    match_status: str


class ContextMatchSummary(BaseModel):
    feedback_id: str
    status: ContextStatus
    matched_context_id: Optional[str] = None
    candidates: list[ContextMatchOut]
