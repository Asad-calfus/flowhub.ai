from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from src.themes.schemas import TrendStatus


class ThemeMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    feedback_id: str
    membership_score: Optional[float] = None


class ThemeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    keywords: list[str]
    feedback_count: int
    first_seen: Optional[date] = None
    last_seen: Optional[date] = None
    trend_status: Optional[TrendStatus] = None


class ThemeDetailOut(ThemeOut):
    sentiment_distribution: dict[str, float]
    representative_feedback: list[dict]
    members: list[ThemeMemberOut]


class RecomputeThemesResponse(BaseModel):
    themes_created: int
    feedback_assigned: int
    feedback_unclustered: int
