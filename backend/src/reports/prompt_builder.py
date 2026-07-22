"""Builds the prompt for the optional LLM report-narrative generator.

The prompt hands over the `EvidencePack` (already computed, already bounded in size -
see `src.reports.evidence_builder`) and nothing else: no raw feedback table, no direct
database access. The model is instructed to return `LLMReportNarrative` JSON only -
wording, never numbers - and to reference only IDs that already appear in the evidence.
"""

import json

from src.reports.schemas import EvidencePack

SYSTEM_PROMPT = (
    "You write the prose for a weekly customer-feedback report for FlowHub, a project "
    "management SaaS product. You are given a JSON 'evidence pack' containing metrics, "
    "themes, product modules, known bugs, feature requests, releases, new-issue clusters, "
    "enterprise feedback, and recommended actions that have ALL ALREADY BEEN CALCULATED "
    "from real data. Your job is only to explain and summarize this evidence in clear "
    "prose - you must NEVER invent, recompute, or change any count, percentage, or trend "
    "label. Every theme_id, context_id, and action_id you reference MUST already appear "
    "in the evidence pack under that exact ID - never invent a new one. Do not mention "
    "any bug, feature request, theme, or customer claim that is not present in the "
    "evidence. Return ONLY a single JSON object matching this schema, no markdown fences, "
    "no commentary:\n\n"
    "{\n"
    '  "executive_summary": str,\n'
    '  "theme_narratives": [{"theme_id": str, "title": str, "description": str}],\n'
    '  "module_narratives": [{"product_module": str, "title": str, "description": str}],\n'
    '  "known_bug_narratives": [{"context_id": str, "title": str, "description": str}],\n'
    '  "feature_request_narratives": [{"context_id": str, "title": str, "description": str}],\n'
    '  "release_narratives": [{"context_id": str, "title": str, "description": str}],\n'
    '  "new_issue_narratives": [{"context_id": str, "title": str, "description": str}],\n'
    '  "enterprise_narrative": {"title": str, "description": str} | null,\n'
    '  "action_narratives": [{"action_id": str, "title": str, "description": str}],\n'
    '  "data_limitations_notes": [str]\n'
    "}\n\n"
    "For new_issue_narratives, use the cluster_id from evidence.new_issue_clusters as "
    "context_id. Keep every description to 1-3 sentences. Do not include numbers you "
    "were not given verbatim in the evidence pack."
)


def build_user_prompt(pack: EvidencePack) -> str:
    return "Evidence pack:\n" + json.dumps(pack.model_dump(mode="json"), ensure_ascii=False)


def build_prompt(pack: EvidencePack) -> tuple[str, str]:
    return SYSTEM_PROMPT, build_user_prompt(pack)
