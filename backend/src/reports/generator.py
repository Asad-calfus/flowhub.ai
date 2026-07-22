"""Deterministic-baseline and optional LLM weekly report generation.

Both paths produce a `LLMReportNarrative` (wording only) and then call `assemble_report`,
which is the ONLY place numeric fields are copied onto the final `WeeklyReport` - always
from the `EvidencePack`/`PeriodAggregate`, never from the narrative. This makes it
structurally impossible for either path to "calculate" or "change" a number.
"""

import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from pydantic import ValidationError

from src.reports.prompt_builder import build_prompt
from src.reports.schemas import (
    ActionNarrative,
    ContextInsight,
    ContextNarrative,
    DataLimitations,
    EnterpriseInsight,
    EnterpriseNarrative,
    EvidencePack,
    LLMReportNarrative,
    ModuleNarrative,
    ProductModuleInsight,
    RecommendedAction,
    ReportingPeriod,
    SupportingEvidence,
    ThemeInsight,
    ThemeNarrative,
    WeeklyReport,
)

load_dotenv()

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_CACHE_PATH = os.path.join(REPO_ROOT, "results", "cache", "report_llm_cache.json")
PROMPT_VERSION = "v1"
MAX_ATTEMPTS = 2

_ACTION_LABELS = {
    "review_bug_priority": "Review bug priority",
    "investigate_new_issue": "Investigate new issue",
    "review_roadmap_priority": "Review roadmap priority",
    "inspect_release": "Inspect recent release",
    "enterprise_follow_up": "Enterprise account follow-up",
    "human_review": "Send for human review",
}


# ---------------------------------------------------------------------------
# Deterministic narrative templates (also used as the dry-run/LLM-unavailable stub)
# ---------------------------------------------------------------------------


def _theme_narrative(theme) -> ThemeNarrative:
    label = ", ".join(theme.keywords[:3]) if theme.keywords else theme.theme_id
    title = f"{label} ({theme.dominant_product_module or 'multiple modules'})"
    change = f", {theme.percent_change:+.1f}% vs previous period" if theme.percent_change is not None else ""
    description = f"{theme.feedback_count} feedback item(s) this period, trend: {theme.trend}{change}."
    return ThemeNarrative(theme_id=theme.theme_id, title=title, description=description)


def _module_narrative(module) -> ModuleNarrative:
    title = f"{module.product_module} — {round(module.negative_ratio * 100)}% negative"
    description = f"{module.feedback_count} feedback item(s) this period, {round(module.negative_ratio * 100)}% negative sentiment."
    return ModuleNarrative(product_module=module.product_module, title=title, description=description)


def _context_narrative(item) -> ContextNarrative:
    change = f", {item.percent_change:+.1f}% vs previous period" if item.percent_change is not None else ""
    description = f"{item.feedback_count} feedback item(s) this period, trend: {item.trend}{change}."
    if item.status:
        description += f" Current status: {item.status}."
    return ContextNarrative(context_id=item.context_id, title=item.title, description=description)


def _new_issue_narrative(cluster) -> ContextNarrative:
    title = f"Untracked cluster: {cluster.cluster_id}"
    description = f"{cluster.feedback_count} feedback item(s) with no confident match to a known bug, feature request, or release."
    return ContextNarrative(context_id=cluster.cluster_id, title=title, description=description)


def _enterprise_narrative(pack: EvidencePack) -> Optional[EnterpriseNarrative]:
    if pack.enterprise.negative_feedback_count == 0:
        return None
    return EnterpriseNarrative(
        title="Enterprise-tier negative feedback",
        description=f"{pack.enterprise.negative_feedback_count} Enterprise-tier feedback item(s) with negative sentiment this period.",
    )


def _action_narrative(action) -> ActionNarrative:
    label = _ACTION_LABELS.get(action.action_type, action.action_type)
    refs = action.related_context_ids + action.related_theme_ids
    ref_text = f" (related: {', '.join(refs)})" if refs else ""
    return ActionNarrative(
        action_id=action.action_id,
        title=label,
        description=f"{label} — priority {action.priority}{ref_text}.",
    )


def _executive_summary(pack: EvidencePack) -> str:
    m = pack.metrics
    top_sentiment = max(m.sentiment_distribution, key=m.sentiment_distribution.get) if m.sentiment_distribution else "unknown"
    growing = sum(1 for t in pack.top_themes if t.trend == "growing")
    period_desc = (
        "across the full dataset (all-time)"
        if pack.period.is_all_time
        else f"from {pack.period.start_date} to {pack.period.end_date}"
    )
    return (
        f"{m.total_feedback} feedback item(s) received {period_desc}. "
        f"Dominant sentiment: {top_sentiment}. {len(pack.top_themes)} theme(s) tracked, {growing} growing. "
        f"{len(pack.known_bugs)} known bug(s) and {len(pack.feature_requests)} feature request(s) received repeated "
        f"reports. {m.new_issue_count} feedback item(s) appear to reference new, untracked issues. "
        f"{pack.enterprise.negative_feedback_count} Enterprise-tier negative report(s) this period."
    )


def build_deterministic_narrative(pack: EvidencePack) -> LLMReportNarrative:
    return LLMReportNarrative(
        executive_summary=_executive_summary(pack),
        theme_narratives=[_theme_narrative(t) for t in pack.top_themes],
        module_narratives=[_module_narrative(m) for m in pack.modules],
        known_bug_narratives=[_context_narrative(b) for b in pack.known_bugs],
        feature_request_narratives=[_context_narrative(f) for f in pack.feature_requests],
        release_narratives=[_context_narrative(r) for r in pack.releases],
        new_issue_narratives=[_new_issue_narrative(c) for c in pack.new_issue_clusters],
        enterprise_narrative=_enterprise_narrative(pack),
        action_narratives=[_action_narrative(a) for a in pack.recommended_actions],
        data_limitations_notes=list(pack.data_limitations),
    )


# ---------------------------------------------------------------------------
# Narrative ID validation - prevents unsupported references (invented IDs)
# ---------------------------------------------------------------------------


class UnsupportedReferenceError(ValueError):
    pass


def validate_narrative_ids(narrative: LLMReportNarrative, pack: EvidencePack) -> None:
    theme_ids = pack.all_theme_ids()
    context_ids = pack.all_context_ids()
    action_ids = pack.all_action_ids()
    cluster_ids = {c.cluster_id for c in pack.new_issue_clusters}
    module_ids = {m.product_module for m in pack.modules}

    bad = [t.theme_id for t in narrative.theme_narratives if t.theme_id not in theme_ids]
    bad += [m.product_module for m in narrative.module_narratives if m.product_module not in module_ids]
    bad += [c.context_id for c in narrative.known_bug_narratives if c.context_id not in context_ids]
    bad += [c.context_id for c in narrative.feature_request_narratives if c.context_id not in context_ids]
    bad += [c.context_id for c in narrative.release_narratives if c.context_id not in context_ids]
    bad += [c.context_id for c in narrative.new_issue_narratives if c.context_id not in cluster_ids]
    bad += [a.action_id for a in narrative.action_narratives if a.action_id not in action_ids]
    if bad:
        raise UnsupportedReferenceError(f"Narrative references unknown IDs not present in evidence pack: {bad}")


# ---------------------------------------------------------------------------
# Assembly: narrative (text) + evidence pack (numbers) -> WeeklyReport
# ---------------------------------------------------------------------------


def _evidence_for_theme(theme) -> SupportingEvidence:
    return SupportingEvidence(
        representative_feedback_ids=[r.feedback_id for r in theme.representative_feedback],
        related_theme_ids=[theme.theme_id],
        evidence_strength="high" if theme.feedback_count >= 3 else "medium",
    )


def assemble_report(
    pack: EvidencePack,
    narrative: LLMReportNarrative,
    generation_method: str,
    model_name: Optional[str],
    product_module_filter: Optional[str],
    customer_tier_filter: Optional[str],
    created_at: Optional[datetime] = None,
) -> WeeklyReport:
    theme_narrative_by_id = {t.theme_id: t for t in narrative.theme_narratives}
    top_pain_points = []
    growing_themes = []
    for t in pack.top_themes:
        n = theme_narrative_by_id.get(t.theme_id)
        insight = ThemeInsight(
            theme_id=t.theme_id,
            title=n.title if n else t.theme_id,
            description=n.description if n else f"{t.feedback_count} feedback item(s), trend {t.trend}.",
            feedback_count=t.feedback_count,
            trend=t.trend,
            percent_change=t.percent_change,
            sentiment_distribution=t.sentiment_distribution,
            product_module=t.dominant_product_module,
            evidence=_evidence_for_theme(t),
        )
        top_pain_points.append(insight)
        if t.trend in ("growing", "new", "all_time"):
            growing_themes.append(insight)
    top_pain_points.sort(key=lambda i: -i.feedback_count)

    module_narrative_by_id = {m.product_module: m for m in narrative.module_narratives}
    most_negative_modules = []
    for m in pack.modules:
        n = module_narrative_by_id.get(m.product_module)
        most_negative_modules.append(
            ProductModuleInsight(
                product_module=m.product_module,
                title=n.title if n else m.product_module,
                description=n.description if n else f"{m.feedback_count} feedback item(s), {m.negative_ratio:.0%} negative.",
                feedback_count=m.feedback_count,
                negative_ratio=m.negative_ratio,
                sentiment_distribution=m.sentiment_distribution,
                evidence=SupportingEvidence(
                    representative_feedback_ids=[r.feedback_id for r in m.representative_feedback],
                    evidence_strength="high" if m.feedback_count >= 5 else "medium",
                ),
            )
        )

    def _context_insights(items, narratives, context_type):
        narrative_by_id = {c.context_id: c for c in narratives}
        out = []
        for item in items:
            n = narrative_by_id.get(item.context_id)
            out.append(
                ContextInsight(
                    context_id=item.context_id,
                    context_type=context_type,
                    title=n.title if n else item.title,
                    description=n.description if n else f"{item.feedback_count} feedback item(s), trend {item.trend}.",
                    feedback_count=item.feedback_count,
                    trend=item.trend,
                    status=item.status,
                    product_module=item.product_module,
                    evidence=SupportingEvidence(
                        representative_feedback_ids=[r.feedback_id for r in item.representative_feedback],
                        related_context_ids=[item.context_id],
                        evidence_strength="high" if item.feedback_count >= 3 else "medium",
                    ),
                )
            )
        return out

    known_bugs_growing = _context_insights(
        [b for b in pack.known_bugs if b.trend in ("growing", "new", "all_time")], narrative.known_bug_narratives, "known_bug"
    )
    feature_requests = _context_insights(pack.feature_requests, narrative.feature_request_narratives, "feature_request")
    release_related_issues = _context_insights(pack.releases, narrative.release_narratives, "release")

    new_issue_narrative_by_id = {c.context_id: c for c in narrative.new_issue_narratives}
    new_untracked_issues = []
    for cluster in pack.new_issue_clusters:
        n = new_issue_narrative_by_id.get(cluster.cluster_id)
        new_untracked_issues.append(
            ContextInsight(
                context_id=cluster.cluster_id,
                context_type="new_issue",
                title=n.title if n else f"Untracked cluster: {cluster.cluster_id}",
                description=n.description if n else f"{cluster.feedback_count} feedback item(s) with no confident context match.",
                feedback_count=cluster.feedback_count,
                trend="new",
                evidence=SupportingEvidence(
                    representative_feedback_ids=[r.feedback_id for r in cluster.representative_feedback],
                    evidence_strength="low",
                ),
            )
        )

    enterprise_feedback = []
    if pack.enterprise.negative_feedback_count:
        n = narrative.enterprise_narrative
        enterprise_feedback.append(
            EnterpriseInsight(
                title=n.title if n else "Enterprise-tier negative feedback",
                description=n.description if n else f"{pack.enterprise.negative_feedback_count} Enterprise-tier negative feedback item(s).",
                feedback_count=pack.enterprise.negative_feedback_count,
                evidence=SupportingEvidence(
                    representative_feedback_ids=[r.feedback_id for r in pack.enterprise.representative_feedback],
                    evidence_strength="high" if pack.enterprise.negative_feedback_count >= 2 else "medium",
                ),
            )
        )

    action_narrative_by_id = {a.action_id: a for a in narrative.action_narratives}
    recommended_actions = []
    for action in pack.recommended_actions:
        n = action_narrative_by_id.get(action.action_id)
        label = _ACTION_LABELS.get(action.action_type, action.action_type)
        recommended_actions.append(
            RecommendedAction(
                action_id=action.action_id,
                action_type=action.action_type,
                title=n.title if n else label,
                description=n.description if n else f"{label} — priority {action.priority}.",
                priority=action.priority,
                evidence=SupportingEvidence(
                    related_theme_ids=action.related_theme_ids,
                    related_context_ids=action.related_context_ids,
                    evidence_strength="high",
                ),
            )
        )

    return WeeklyReport(
        period=pack.period,
        product_module_filter=product_module_filter,
        customer_tier_filter=customer_tier_filter,
        executive_summary=narrative.executive_summary,
        summary_metrics=pack.metrics,
        top_pain_points=top_pain_points[:8],
        growing_themes=growing_themes,
        most_negative_modules=most_negative_modules,
        feature_requests=feature_requests,
        known_bugs_growing=known_bugs_growing,
        release_related_issues=release_related_issues,
        enterprise_feedback=enterprise_feedback,
        new_untracked_issues=new_untracked_issues,
        recommended_actions=recommended_actions,
        data_limitations=DataLimitations(notes=narrative.data_limitations_notes or list(pack.data_limitations)),
        generation_method=generation_method,
        model_name=model_name,
        prompt_version=PROMPT_VERSION if generation_method != "deterministic" else None,
        created_at=created_at,
    )


def generate_deterministic_report(
    pack: EvidencePack,
    product_module_filter: Optional[str] = None,
    customer_tier_filter: Optional[str] = None,
    created_at: Optional[datetime] = None,
) -> WeeklyReport:
    narrative = build_deterministic_narrative(pack)
    return assemble_report(pack, narrative, "deterministic", None, product_module_filter, customer_tier_filter, created_at)


# ---------------------------------------------------------------------------
# Optional LLM narrative generator
# ---------------------------------------------------------------------------


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1] if text.count("```") >= 2 else text.strip("`")
        text = text.strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    return text


def _pack_cache_key(pack: EvidencePack) -> str:
    payload = pack.model_dump(mode="json")
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return f"{pack.period.start_date}_{pack.period.end_date}_{digest[:16]}"


@dataclass
class ReportGenerationResult:
    narrative: Optional[LLMReportNarrative]
    error: Optional[str] = None
    retries: int = 0
    latency_seconds: float = 0.0
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    from_cache: bool = False
    dry_run: bool = False


class LLMReportGenerator:
    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        dry_run: Optional[bool] = None,
        cache_path: str = DEFAULT_CACHE_PATH,
        timeout: Optional[float] = None,
    ):
        self.provider = (provider or os.environ.get("LLM_PROVIDER", "anthropic")).lower()
        self.model = model or os.environ.get("LLM_MODEL", "")
        self.api_key = api_key or os.environ.get(self._api_key_env_var(), "")
        self.timeout = timeout or float(os.environ.get("LLM_TIMEOUT_SECONDS", "30"))
        self.dry_run = dry_run if dry_run is not None else not bool(self.api_key)
        self.cache_path = cache_path
        self._client = None
        self.cache = self._load_cache()

    def _api_key_env_var(self) -> str:
        return "OPENAI_API_KEY" if self.provider == "openai" else "ANTHROPIC_API_KEY"

    def _load_cache(self) -> dict:
        if os.path.exists(self.cache_path):
            with open(self.cache_path, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_cache(self) -> None:
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, indent=2)

    def _call_llm(self, system_prompt: str, user_prompt: str, pack: EvidencePack) -> tuple[str, dict, float]:
        start = time.perf_counter()
        if self.dry_run:
            stub = build_deterministic_narrative(pack)
            raw = json.dumps(stub.model_dump())
            return raw, {"input_tokens": 0, "output_tokens": 0}, time.perf_counter() - start
        if self.provider == "openai":
            return self._call_openai(system_prompt, user_prompt, start)
        return self._call_anthropic(system_prompt, user_prompt, start)

    def _call_anthropic(self, system_prompt: str, user_prompt: str, start: float) -> tuple[str, dict, float]:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self.api_key, timeout=self.timeout)
        response = self._client.messages.create(
            model=self.model, max_tokens=2000, system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        latency = time.perf_counter() - start
        text = "".join(block.text for block in response.content if hasattr(block, "text"))
        usage = {
            "input_tokens": getattr(response.usage, "input_tokens", None),
            "output_tokens": getattr(response.usage, "output_tokens", None),
        }
        return text, usage, latency

    def _call_openai(self, system_prompt: str, user_prompt: str, start: float) -> tuple[str, dict, float]:
        if self._client is None:
            import openai

            self._client = openai.OpenAI(api_key=self.api_key, timeout=self.timeout)
        response = self._client.chat.completions.create(
            model=self.model, max_tokens=2000, response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        )
        latency = time.perf_counter() - start
        text = response.choices[0].message.content or ""
        usage = {
            "input_tokens": getattr(response.usage, "prompt_tokens", None),
            "output_tokens": getattr(response.usage, "completion_tokens", None),
        }
        return text, usage, latency

    def generate(self, pack: EvidencePack, force: bool = False) -> ReportGenerationResult:
        cache_key = _pack_cache_key(pack)
        if not force and cache_key in self.cache:
            cached = self.cache[cache_key]
            if cached.get("narrative") is not None:
                return ReportGenerationResult(
                    narrative=LLMReportNarrative(**cached["narrative"]),
                    retries=cached.get("retries", 0),
                    latency_seconds=cached.get("latency_seconds", 0.0),
                    input_tokens=cached.get("input_tokens"),
                    output_tokens=cached.get("output_tokens"),
                    from_cache=True,
                    dry_run=cached.get("dry_run", False),
                )

        system_prompt, user_prompt = build_prompt(pack)
        last_error = None
        total_latency = 0.0
        total_in = 0
        total_out = 0

        for attempt in range(MAX_ATTEMPTS):
            raw, usage, latency = self._call_llm(system_prompt, user_prompt, pack)
            total_latency += latency
            total_in += usage.get("input_tokens") or 0
            total_out += usage.get("output_tokens") or 0
            try:
                parsed = json.loads(_strip_json_fences(raw))
                narrative = LLMReportNarrative(**parsed)
                validate_narrative_ids(narrative, pack)
                result = ReportGenerationResult(
                    narrative=narrative, retries=attempt, latency_seconds=total_latency,
                    input_tokens=total_in or None, output_tokens=total_out or None, dry_run=self.dry_run,
                )
                self.cache[cache_key] = {
                    "narrative": narrative.model_dump(), "retries": attempt, "latency_seconds": total_latency,
                    "input_tokens": total_in or None, "output_tokens": total_out or None, "dry_run": self.dry_run,
                }
                self._save_cache()
                return result
            except (json.JSONDecodeError, ValidationError, UnsupportedReferenceError) as exc:
                last_error = str(exc)
                user_prompt = (
                    user_prompt + f"\n\nYour previous response was invalid ({last_error[:300]}). "
                    "Return ONLY a single valid JSON object matching the required schema, "
                    "referencing only IDs already present in the evidence pack."
                )

        return ReportGenerationResult(
            narrative=None, error=last_error, retries=MAX_ATTEMPTS - 1, latency_seconds=total_latency,
            input_tokens=total_in or None, output_tokens=total_out or None, dry_run=self.dry_run,
        )


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def _render_evidence(evidence: SupportingEvidence) -> str:
    parts = []
    if evidence.representative_feedback_ids:
        parts.append(f"feedback: {', '.join(evidence.representative_feedback_ids)}")
    if evidence.related_context_ids:
        parts.append(f"context: {', '.join(evidence.related_context_ids)}")
    if evidence.related_theme_ids:
        parts.append(f"themes: {', '.join(evidence.related_theme_ids)}")
    ref = "; ".join(parts)
    return f"  _Evidence ({evidence.evidence_strength}): {ref}_" if ref else f"  _Evidence: {evidence.evidence_strength}_"


def render_markdown(report: WeeklyReport) -> str:
    period_label = (
        f"All-time (as of {report.period.end_date})"
        if report.period.is_all_time
        else f"{report.period.start_date} to {report.period.end_date}"
    )
    lines = [f"# Weekly Customer Feedback Report: {period_label}", ""]
    if report.product_module_filter or report.customer_tier_filter:
        lines.append(f"_Filters: module={report.product_module_filter or 'all'}, tier={report.customer_tier_filter or 'all'}_")
        lines.append("")

    lines += ["## 1. Executive Summary", "", report.executive_summary, ""]

    m = report.summary_metrics
    lines += [
        "## 2. Total Feedback Received", "",
        f"**{m.total_feedback}** feedback item(s).",
        f"- By source: {m.feedback_by_source}",
        f"- By type: {m.feedback_by_type}",
        f"- Sentiment distribution: {m.sentiment_distribution}",
        f"- By product module: {m.feedback_by_product_module}",
        f"- By customer tier: {m.feedback_by_customer_tier}",
        f"- Average classification confidence: {m.average_confidence}",
        "",
    ]

    lines += ["## 3. Top Customer Pain Points", ""]
    for t in report.top_pain_points:
        lines += [f"### {t.title}", t.description, _render_evidence(t.evidence), ""]

    lines += ["## 4. Growing Themes", ""]
    for t in report.growing_themes:
        lines += [f"### {t.title} ({t.trend})", t.description, _render_evidence(t.evidence), ""]

    lines += ["## 5. Most Negative Product Modules", ""]
    for mo in report.most_negative_modules:
        lines += [f"### {mo.title}", mo.description, _render_evidence(mo.evidence), ""]

    lines += ["## 6. Frequently Requested Features", ""]
    for f in report.feature_requests:
        lines += [f"### {f.title}", f.description, _render_evidence(f.evidence), ""]

    lines += ["## 7. Known Bugs Receiving Additional Reports", ""]
    for b in report.known_bugs_growing:
        lines += [f"### {b.title}", b.description, _render_evidence(b.evidence), ""]

    lines += ["## 8. Possible Release-Related Issues", ""]
    for r in report.release_related_issues:
        lines += [f"### {r.title}", r.description, _render_evidence(r.evidence), ""]

    lines += ["## 9. Important Enterprise Customer Feedback", ""]
    for e in report.enterprise_feedback:
        lines += [f"### {e.title}", e.description, _render_evidence(e.evidence), ""]
    if not report.enterprise_feedback:
        lines += ["No notable Enterprise-tier negative feedback this period.", ""]

    lines += ["## 10. New or Untracked Issues", ""]
    for issue in report.new_untracked_issues:
        lines += [f"### {issue.title}", issue.description, _render_evidence(issue.evidence), ""]

    lines += ["## 11. Recommended Actions", ""]
    for a in report.recommended_actions:
        lines += [f"### [{a.priority}] {a.title}", a.description, _render_evidence(a.evidence), ""]

    lines += ["## 12. Data Limitations", ""]
    for note in report.data_limitations.notes:
        lines.append(f"- {note}")
    if not report.data_limitations.notes:
        lines.append("None noted for this period.")
    lines.append("")

    lines += [
        "---",
        f"_Generated by: {report.generation_method}"
        + (f" ({report.model_name})" if report.model_name else "")
        + (f", prompt {report.prompt_version}" if report.prompt_version else "")
        + (f", at {report.created_at}" if report.created_at else "")
        + "_",
    ]
    return "\n".join(lines)
