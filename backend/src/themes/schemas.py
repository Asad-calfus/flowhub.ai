"""Validated structures for the theme clustering pipeline. `theme_hint` is deliberately
absent from every schema below - it is read only by `src/themes/evaluator.py`, never by
clustering, keyword extraction, naming, or trend code.
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

TrendStatus = Literal["new", "growing", "stable", "declining", "all_time"]


class ThemeAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feedback_id: str
    theme_id: Optional[str] = None  # None -> unclustered


class WeeklyThemeStat(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme_id: str
    week_start: str
    feedback_count: int = Field(ge=0)
    change_from_previous_week: Optional[int] = None
    percent_change: Optional[float] = None
    sentiment_distribution: dict[str, float] = Field(default_factory=dict)
    customer_tier_distribution: dict[str, float] = Field(default_factory=dict)
    product_module_distribution: dict[str, float] = Field(default_factory=dict)
    trend_status: TrendStatus


class Theme(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme_id: str
    name: str
    size: int = Field(ge=1)
    keywords: list[str] = Field(default_factory=list)
    representative_feedback_ids: list[str] = Field(default_factory=list)
    dominant_product_module: Optional[str] = None
    sentiment_distribution: dict[str, float] = Field(default_factory=dict)
    product_module_distribution: dict[str, float] = Field(default_factory=dict)
    first_seen: str
    last_seen: str
    weekly_trends: list[WeeklyThemeStat] = Field(default_factory=list)
