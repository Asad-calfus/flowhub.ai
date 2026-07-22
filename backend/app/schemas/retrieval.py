from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

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


class RetrievalBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feedback_ids: Optional[list[str]] = Field(
        default=None,
        description="Specific feedback IDs to run context-matching for; omit to run it for "
        "every feedback record in the workspace that has no context-match rows yet.",
    )
    top_k: int = 5


class RetrievalBatchResultItem(BaseModel):
    feedback_id: str
    status: Literal["success", "failed"]
    error: Optional[str] = None


class RetrievalBatchResponse(BaseModel):
    requested: int
    succeeded: int
    failed: int
    results: list[RetrievalBatchResultItem]
