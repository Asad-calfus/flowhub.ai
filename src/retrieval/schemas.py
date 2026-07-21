"""Validated structures for the retrieval pipeline. Reuses the classification leakage
guard (src/classification/schemas.py) rather than duplicating it - retrieval input is the
same allowed-fields contract as the classifier.
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.classification.schemas import (  # noqa: F401 - re-exported for retrieval callers
    ALLOWED_INPUT_FIELDS,
    LEAKAGE_FIELDS,
    ClassifierInput,
    LeakageError,
    assert_no_leakage,
    strip_leakage_fields,
)

ContextType = Literal["known_bug", "feature_request", "release"]

ContextStatus = Literal[
    "known_bug",
    "duplicate_feature_request",
    "possible_release_issue",
    "new_untracked_issue",
    "no_confident_match",
]


class SimilarFeedbackMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feedback_id: str
    matched_feedback_id: str
    rank: int = Field(ge=1)
    similarity_score: float = Field(ge=-1.0, le=1.0)
    text_preview: str


class ContextCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context_id: str
    context_type: ContextType
    title: str
    rank: int = Field(ge=1)
    similarity_score: float = Field(ge=-1.0, le=1.0)


class ContextMatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feedback_id: str
    status: ContextStatus
    matched_context_id: Optional[str] = None
    bugs: list[ContextCandidate] = Field(default_factory=list)
    feature_requests: list[ContextCandidate] = Field(default_factory=list)
    releases: list[ContextCandidate] = Field(default_factory=list)
