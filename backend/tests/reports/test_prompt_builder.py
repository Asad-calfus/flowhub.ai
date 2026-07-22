import json

from src.reports.prompt_builder import build_prompt
from tests.reports.factories import make_evidence_pack


def test_user_prompt_contains_only_evidence_pack_fields():
    pack = make_evidence_pack()
    _, user_prompt = build_prompt(pack)
    payload = json.loads(user_prompt.split("Evidence pack:\n", 1)[1])
    assert payload["metrics"]["total_feedback"] == pack.metrics.total_feedback
    assert set(payload.keys()) == set(pack.model_dump(mode="json").keys())


def test_system_prompt_forbids_inventing_ids():
    system_prompt, _ = build_prompt(make_evidence_pack())
    assert "never invent" in system_prompt.lower() or "must never invent" in system_prompt.lower()
