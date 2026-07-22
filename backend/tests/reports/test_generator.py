import json

from src.reports.generator import (
    LLMReportGenerator,
    UnsupportedReferenceError,
    assemble_report,
    build_deterministic_narrative,
    generate_deterministic_report,
    render_markdown,
    validate_narrative_ids,
)
from tests.reports.factories import make_evidence_pack


def _valid_narrative_dict(pack):
    narrative = build_deterministic_narrative(pack)
    return narrative.model_dump()


def test_deterministic_report_numbers_match_evidence_pack_exactly():
    pack = make_evidence_pack()
    report = generate_deterministic_report(pack)
    assert report.generation_method == "deterministic"
    assert report.summary_metrics == pack.metrics
    assert report.top_pain_points[0].feedback_count == pack.top_themes[0].feedback_count
    assert report.top_pain_points[0].trend == pack.top_themes[0].trend


def test_deterministic_report_never_invents_ids():
    pack = make_evidence_pack()
    report = generate_deterministic_report(pack)
    theme_ids = {t.theme_id for t in report.top_pain_points}
    assert theme_ids <= pack.all_theme_ids()


def test_validate_narrative_ids_accepts_known_ids():
    pack = make_evidence_pack()
    narrative = build_deterministic_narrative(pack)
    validate_narrative_ids(narrative, pack)  # should not raise


def test_validate_narrative_ids_rejects_invented_theme_id():
    pack = make_evidence_pack()
    narrative = build_deterministic_narrative(pack)
    narrative.theme_narratives[0].theme_id = "THM-INVENTED"
    try:
        validate_narrative_ids(narrative, pack)
        assert False, "expected UnsupportedReferenceError"
    except UnsupportedReferenceError as exc:
        assert "THM-INVENTED" in str(exc)


def test_render_markdown_contains_all_twelve_sections():
    pack = make_evidence_pack()
    report = generate_deterministic_report(pack)
    md = render_markdown(report)
    for n in range(1, 13):
        assert f"## {n}." in md


def test_llm_generator_dry_run_never_calls_network(tmp_path, monkeypatch):
    pack = make_evidence_pack()
    gen = LLMReportGenerator(dry_run=True, cache_path=str(tmp_path / "cache.json"))

    def fail_if_called(*args, **kwargs):
        raise AssertionError("network should never be called in dry-run mode")

    monkeypatch.setattr("anthropic.Anthropic", fail_if_called, raising=False)
    result = gen.generate(pack)
    assert result.narrative is not None
    assert result.dry_run is True


def test_llm_generator_retries_once_on_invalid_json_then_succeeds(tmp_path):
    pack = make_evidence_pack()
    gen = LLMReportGenerator(dry_run=False, api_key="x", cache_path=str(tmp_path / "cache.json"))
    calls = {"n": 0}
    valid = json.dumps(_valid_narrative_dict(pack))

    def fake_call(system_prompt, user_prompt, p):
        calls["n"] += 1
        if calls["n"] == 1:
            return "not json {broken", {"input_tokens": 5, "output_tokens": 5}, 0.01
        return valid, {"input_tokens": 5, "output_tokens": 5}, 0.01

    gen._call_llm = fake_call
    result = gen.generate(pack)
    assert calls["n"] == 2
    assert result.retries == 1
    assert result.narrative is not None


def test_llm_generator_retry_limit_records_failure(tmp_path):
    pack = make_evidence_pack()
    gen = LLMReportGenerator(dry_run=False, api_key="x", cache_path=str(tmp_path / "cache.json"))

    def always_bad(system_prompt, user_prompt, p):
        return "not json {broken", {"input_tokens": 1, "output_tokens": 1}, 0.01

    gen._call_llm = always_bad
    result = gen.generate(pack)
    assert result.narrative is None
    assert result.error is not None


def test_llm_generator_rejects_unsupported_reference_and_retries(tmp_path):
    pack = make_evidence_pack()
    gen = LLMReportGenerator(dry_run=False, api_key="x", cache_path=str(tmp_path / "cache.json"))
    calls = {"n": 0}
    bad_narrative = _valid_narrative_dict(pack)
    bad_narrative["theme_narratives"][0]["theme_id"] = "THM-MADE-UP"
    valid = json.dumps(_valid_narrative_dict(pack))

    def fake_call(system_prompt, user_prompt, p):
        calls["n"] += 1
        if calls["n"] == 1:
            return json.dumps(bad_narrative), {"input_tokens": 5, "output_tokens": 5}, 0.01
        return valid, {"input_tokens": 5, "output_tokens": 5}, 0.01

    gen._call_llm = fake_call
    result = gen.generate(pack)
    assert calls["n"] == 2
    assert result.narrative is not None


def test_llm_generator_cache_hit_skips_regeneration(tmp_path):
    pack = make_evidence_pack()
    cache_path = str(tmp_path / "cache.json")
    gen = LLMReportGenerator(dry_run=False, api_key="x", cache_path=cache_path)
    calls = {"n": 0}
    valid = json.dumps(_valid_narrative_dict(pack))

    def fake_call(system_prompt, user_prompt, p):
        calls["n"] += 1
        return valid, {"input_tokens": 1, "output_tokens": 1}, 0.01

    gen._call_llm = fake_call
    gen.generate(pack)
    assert calls["n"] == 1
    result2 = gen.generate(pack)
    assert calls["n"] == 1
    assert result2.from_cache is True


def test_llm_generator_force_bypasses_cache(tmp_path):
    pack = make_evidence_pack()
    gen = LLMReportGenerator(dry_run=False, api_key="x", cache_path=str(tmp_path / "cache.json"))
    calls = {"n": 0}
    valid = json.dumps(_valid_narrative_dict(pack))

    def fake_call(system_prompt, user_prompt, p):
        calls["n"] += 1
        return valid, {"input_tokens": 1, "output_tokens": 1}, 0.01

    gen._call_llm = fake_call
    gen.generate(pack)
    gen.generate(pack, force=True)
    assert calls["n"] == 2


def test_assemble_report_uses_narrative_text_but_pack_numbers():
    pack = make_evidence_pack()
    narrative = build_deterministic_narrative(pack)
    narrative.theme_narratives[0].title = "Custom wording from LLM"
    report = assemble_report(pack, narrative, "llm", "anthropic:claude-haiku-4-5-20251001", None, None)
    assert report.top_pain_points[0].title == "Custom wording from LLM"
    assert report.top_pain_points[0].feedback_count == pack.top_themes[0].feedback_count
