import pytest
from pydantic import ValidationError

from src.reports.schemas import (
    MAX_CONTEXT_PER_SECTION,
    MAX_REPRESENTATIVES,
    MAX_THEMES,
    SummaryMetrics,
    SupportingEvidence,
)
from tests.reports.factories import make_evidence_pack


def test_evidence_pack_id_lookup_helpers():
    pack = make_evidence_pack()
    assert pack.all_theme_ids() == {"THM-001"}
    assert pack.all_context_ids() == {"BUG-001", "FR-001", "v2.4.0"}
    assert pack.all_action_ids() == {"ACT-001"}


def test_summary_metrics_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        SummaryMetrics(total_feedback=1, made_up_field=True)


def test_supporting_evidence_defaults_to_medium_strength():
    evidence = SupportingEvidence()
    assert evidence.evidence_strength == "medium"
    assert evidence.representative_feedback_ids == []


def test_evidence_limits_are_reasonably_small():
    assert MAX_THEMES <= 8
    assert MAX_CONTEXT_PER_SECTION <= 5
    assert MAX_REPRESENTATIVES <= 3
