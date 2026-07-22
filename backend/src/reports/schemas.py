"""Validated structures for the weekly insight report pipeline.

Every numeric field on every schema below (counts, percentages, trends, distributions)
is filled in by `src.reports.aggregator` from stored data - never by an LLM. The LLM
report path (`src.reports.generator.generate_llm_report`) only ever supplies *text*
(titles, descriptions, wording) constrained to reference IDs that already exist in the
`EvidencePack` handed to it; see `src.reports.prompt_builder` for how that's enforced.
"""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.themes.schemas import TrendStatus

EvidenceStrength = Literal["high", "medium", "low"]

GenerationMethod = Literal["deterministic", "dry_run", "llm"]

RecommendedActionType = Literal[
    "review_bug_priority",
    "investigate_new_issue",
    "review_roadmap_priority",
    "inspect_release",
    "enterprise_follow_up",
    "human_review",
]


# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------


class ReportingPeriod(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_date: date
    end_date: date
    previous_period_start: Optional[date] = None
    previous_period_end: Optional[date] = None
    is_all_time: bool = False


class SupportingEvidence(BaseModel):
    """Every insight carries one of these so a reader can verify it against raw data."""

    model_config = ConfigDict(extra="forbid")

    representative_feedback_ids: list[str] = Field(default_factory=list)
    related_context_ids: list[str] = Field(default_factory=list)
    related_theme_ids: list[str] = Field(default_factory=list)
    evidence_strength: EvidenceStrength = "medium"


class SummaryMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_feedback: int = Field(ge=0)
    feedback_by_source: dict[str, int] = Field(default_factory=dict)
    feedback_by_type: dict[str, int] = Field(default_factory=dict)
    sentiment_distribution: dict[str, float] = Field(default_factory=dict)
    feedback_by_product_module: dict[str, int] = Field(default_factory=dict)
    feedback_by_customer_tier: dict[str, int] = Field(default_factory=dict)
    new_issue_count: int = Field(ge=0, default=0)
    low_confidence_count: int = Field(ge=0, default=0)
    average_confidence: Optional[float] = None


class ThemeInsight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme_id: str
    title: str
    description: str
    feedback_count: int = Field(ge=0)
    trend: TrendStatus
    percent_change: Optional[float] = None
    sentiment_distribution: dict[str, float] = Field(default_factory=dict)
    product_module: Optional[str] = None
    evidence: SupportingEvidence


class ProductModuleInsight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_module: str
    title: str
    description: str
    feedback_count: int = Field(ge=0)
    negative_ratio: float = Field(ge=0.0, le=1.0)
    sentiment_distribution: dict[str, float] = Field(default_factory=dict)
    evidence: SupportingEvidence


class ContextInsight(BaseModel):
    """One known bug / feature request / release-related cluster of feedback."""

    model_config = ConfigDict(extra="forbid")

    context_id: str
    context_type: Literal["known_bug", "feature_request", "release", "new_issue"]
    title: str
    description: str
    feedback_count: int = Field(ge=0)
    trend: TrendStatus
    status: Optional[str] = None
    product_module: Optional[str] = None
    evidence: SupportingEvidence


class RecommendedAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str
    action_type: RecommendedActionType
    title: str
    description: str
    priority: Literal["Low", "Medium", "High"]
    evidence: SupportingEvidence


class EnterpriseInsight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    description: str
    feedback_count: int = Field(ge=0)
    evidence: SupportingEvidence


class DataLimitations(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Complete weekly report
# ---------------------------------------------------------------------------


class WeeklyReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: Optional[str] = None
    period: ReportingPeriod
    product_module_filter: Optional[str] = None
    customer_tier_filter: Optional[str] = None

    executive_summary: str
    summary_metrics: SummaryMetrics
    top_pain_points: list[ThemeInsight] = Field(default_factory=list)
    growing_themes: list[ThemeInsight] = Field(default_factory=list)
    most_negative_modules: list[ProductModuleInsight] = Field(default_factory=list)
    feature_requests: list[ContextInsight] = Field(default_factory=list)
    known_bugs_growing: list[ContextInsight] = Field(default_factory=list)
    release_related_issues: list[ContextInsight] = Field(default_factory=list)
    enterprise_feedback: list[EnterpriseInsight] = Field(default_factory=list)
    new_untracked_issues: list[ContextInsight] = Field(default_factory=list)
    recommended_actions: list[RecommendedAction] = Field(default_factory=list)
    data_limitations: DataLimitations

    generation_method: GenerationMethod
    model_name: Optional[str] = None
    prompt_version: Optional[str] = None
    created_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# LLM structured-output contract (text only - see module docstring)
# ---------------------------------------------------------------------------


class ThemeNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme_id: str
    title: str
    description: str


class ModuleNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_module: str
    title: str
    description: str


class ContextNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context_id: str
    title: str
    description: str


class ActionNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str
    title: str
    description: str


class EnterpriseNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    description: str


class LLMReportNarrative(BaseModel):
    """Strict structured output the LLM must produce. Contains wording only - no
    counts, percentages, or trend labels anywhere in this schema. Every *_id field is
    validated post-hoc (`src.reports.generator._validate_narrative_ids`) against the IDs
    actually present in the `EvidencePack` it was given; an invented ID is rejected."""

    model_config = ConfigDict(extra="forbid")

    executive_summary: str
    theme_narratives: list[ThemeNarrative] = Field(default_factory=list)
    module_narratives: list[ModuleNarrative] = Field(default_factory=list)
    known_bug_narratives: list[ContextNarrative] = Field(default_factory=list)
    feature_request_narratives: list[ContextNarrative] = Field(default_factory=list)
    release_narratives: list[ContextNarrative] = Field(default_factory=list)
    new_issue_narratives: list[ContextNarrative] = Field(default_factory=list)
    enterprise_narrative: Optional[EnterpriseNarrative] = None
    action_narratives: list[ActionNarrative] = Field(default_factory=list)
    data_limitations_notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Evidence pack (compact, bounded - the only thing the LLM ever sees)
# ---------------------------------------------------------------------------

MAX_THEMES = 8
MAX_CONTEXT_PER_SECTION = 5
MAX_REPRESENTATIVES = 3


class RepresentativeFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feedback_id: str
    text_preview: str = Field(max_length=240)
    sentiment: Optional[str] = None
    customer_tier: Optional[str] = None


class EvidenceTheme(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme_id: str
    keywords: list[str] = Field(default_factory=list)
    dominant_product_module: Optional[str] = None
    feedback_count: int
    percent_change: Optional[float] = None
    trend: TrendStatus
    sentiment_distribution: dict[str, float] = Field(default_factory=dict)
    representative_feedback: list[RepresentativeFeedback] = Field(default_factory=list)


class EvidenceModule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_module: str
    feedback_count: int
    negative_ratio: float
    sentiment_distribution: dict[str, float] = Field(default_factory=dict)
    representative_feedback: list[RepresentativeFeedback] = Field(default_factory=list)


class EvidenceContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context_id: str
    context_type: Literal["known_bug", "feature_request", "release"]
    title: str
    status: Optional[str] = None
    product_module: Optional[str] = None
    feedback_count: int
    percent_change: Optional[float] = None
    trend: TrendStatus
    representative_feedback: list[RepresentativeFeedback] = Field(default_factory=list)


class EvidenceNewIssueCluster(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cluster_id: str
    feedback_count: int
    representative_feedback: list[RepresentativeFeedback] = Field(default_factory=list)


class EvidenceEnterprise(BaseModel):
    model_config = ConfigDict(extra="forbid")

    negative_feedback_count: int
    representative_feedback: list[RepresentativeFeedback] = Field(default_factory=list)


class EvidenceRecommendedAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str
    action_type: RecommendedActionType
    priority: Literal["Low", "Medium", "High"]
    related_theme_ids: list[str] = Field(default_factory=list)
    related_context_ids: list[str] = Field(default_factory=list)


class EvidencePack(BaseModel):
    """Compact, size-bounded evidence handed to the LLM (and used to build the
    deterministic baseline). No raw feedback beyond the sampled representatives is
    ever included - see MAX_* constants above."""

    model_config = ConfigDict(extra="forbid")

    period: ReportingPeriod
    metrics: SummaryMetrics
    top_themes: list[EvidenceTheme] = Field(default_factory=list)
    modules: list[EvidenceModule] = Field(default_factory=list)
    known_bugs: list[EvidenceContext] = Field(default_factory=list)
    feature_requests: list[EvidenceContext] = Field(default_factory=list)
    releases: list[EvidenceContext] = Field(default_factory=list)
    new_issue_clusters: list[EvidenceNewIssueCluster] = Field(default_factory=list)
    enterprise: EvidenceEnterprise
    recommended_actions: list[EvidenceRecommendedAction] = Field(default_factory=list)
    data_limitations: list[str] = Field(default_factory=list)

    def all_theme_ids(self) -> set[str]:
        return {t.theme_id for t in self.top_themes}

    def all_context_ids(self) -> set[str]:
        return (
            {c.context_id for c in self.known_bugs}
            | {c.context_id for c in self.feature_requests}
            | {c.context_id for c in self.releases}
        )

    def all_action_ids(self) -> set[str]:
        return {a.action_id for a in self.recommended_actions}
