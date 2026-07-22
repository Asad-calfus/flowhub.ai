"""Evaluates a generated `WeeklyReport` against the `EvidencePack` it was built from.

Everything here is a deterministic check - no LLM judge. Human-scored fields
(correctness/clarity/usefulness/evidence_quality/actionability, 1-5) are left as `None`
placeholders for a person to fill in; see `backend/results/reports/report_evaluation.json`.
"""

from dataclasses import dataclass, field
from typing import Optional

from src.reports.schemas import EvidencePack, WeeklyReport

MANUAL_RUBRIC_FIELDS = ["correctness", "clarity", "usefulness", "evidence_quality", "actionability"]


@dataclass
class ReportEvaluation:
    metric_correctness: bool
    theme_coverage: float
    important_issue_coverage: float
    evidence_traceability_rate: float
    unsupported_claim_count: int
    recommendation_support_rate: float
    schema_success: bool
    generation_latency_seconds: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    retries: int = 0
    manual_rubric: dict = field(default_factory=lambda: {k: None for k in MANUAL_RUBRIC_FIELDS})
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "metric_correctness": self.metric_correctness,
            "theme_coverage": self.theme_coverage,
            "important_issue_coverage": self.important_issue_coverage,
            "evidence_traceability_rate": self.evidence_traceability_rate,
            "unsupported_claim_count": self.unsupported_claim_count,
            "recommendation_support_rate": self.recommendation_support_rate,
            "schema_success": self.schema_success,
            "generation_latency_seconds": self.generation_latency_seconds,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "retries": self.retries,
            "manual_rubric": self.manual_rubric,
            "notes": self.notes,
        }


def _has_evidence(evidence) -> bool:
    return bool(evidence.representative_feedback_ids or evidence.related_context_ids or evidence.related_theme_ids)


def _theme_rep_ids(pack: EvidencePack) -> dict[str, set]:
    return {t.theme_id: {r.feedback_id for r in t.representative_feedback} for t in pack.top_themes}


def _context_rep_ids(pack: EvidencePack) -> dict[str, set]:
    ids = {}
    for c in pack.known_bugs + pack.feature_requests + pack.releases:
        ids[c.context_id] = {r.feedback_id for r in c.representative_feedback}
    return ids


def evaluate_report(
    report: WeeklyReport,
    pack: EvidencePack,
    generation_latency_seconds: Optional[float] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    estimated_cost_usd: Optional[float] = None,
    retries: int = 0,
) -> ReportEvaluation:
    notes: list[str] = []

    metric_correctness = report.summary_metrics == pack.metrics
    if not metric_correctness:
        notes.append("report.summary_metrics diverges from the evidence pack metrics it was built from.")

    theme_rep_ids = _theme_rep_ids(pack)
    context_rep_ids = _context_rep_ids(pack)

    all_insights = (
        report.top_pain_points
        + report.growing_themes
        + report.most_negative_modules
        + report.feature_requests
        + report.known_bugs_growing
        + report.release_related_issues
        + report.enterprise_feedback
        + report.new_untracked_issues
    )
    unsupported = sum(1 for insight in all_insights if not _has_evidence(insight.evidence))

    traceable = 0
    checked = 0
    for insight in report.top_pain_points + report.growing_themes:
        checked += 1
        allowed = theme_rep_ids.get(insight.theme_id, set())
        if set(insight.evidence.representative_feedback_ids) <= allowed:
            traceable += 1
    for insight in report.feature_requests + report.known_bugs_growing + report.release_related_issues:
        checked += 1
        allowed = context_rep_ids.get(insight.context_id, set())
        if set(insight.evidence.representative_feedback_ids) <= allowed:
            traceable += 1
    evidence_traceability_rate = round(traceable / checked, 4) if checked else 1.0

    theme_coverage = round(len(report.top_pain_points) / len(pack.top_themes), 4) if pack.top_themes else 1.0

    important_total = len(pack.known_bugs) + len(pack.feature_requests) + len(pack.releases)
    important_covered = len(report.known_bugs_growing) + len(report.feature_requests) + len(report.release_related_issues)
    important_issue_coverage = round(important_covered / important_total, 4) if important_total else 1.0

    recommendation_support_rate = (
        round(sum(1 for a in report.recommended_actions if _has_evidence(a.evidence)) / len(report.recommended_actions), 4)
        if report.recommended_actions
        else 1.0
    )

    return ReportEvaluation(
        metric_correctness=metric_correctness,
        theme_coverage=theme_coverage,
        important_issue_coverage=important_issue_coverage,
        evidence_traceability_rate=evidence_traceability_rate,
        unsupported_claim_count=unsupported,
        recommendation_support_rate=recommendation_support_rate,
        schema_success=True,
        generation_latency_seconds=generation_latency_seconds,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=estimated_cost_usd,
        retries=retries,
        notes=notes,
    )
