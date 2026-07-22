from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CopilotAskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)
    live: bool = False  # opt-in real LLM call; dry-run (deterministic) by default


class CopilotSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feedback_id: str
    text_preview: str
    sentiment: Optional[str] = None
    similarity_score: float


class CopilotAnswerOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    answer: str
    model_name: str
    sources: list[CopilotSource] = Field(default_factory=list)
