import json
import os

from src.classification.classifier import FewShotClassifier, MAX_ATTEMPTS
from src.classification.schemas import ClassifierInput

VALID_JSON = json.dumps({
    "feedback_type": "Bug report",
    "category": "Technical Issue",
    "product_module": "Mobile App",
    "sentiment": "Negative",
    "urgency": "High",
    "confidence": 0.9,
    "reasoning": "Crash report.",
})

INVALID_JSON_TEXT = "not json at all {broken"
SCHEMA_INVALID_JSON = json.dumps({"feedback_type": "Not A Real Type"})


def _classifier(tmp_cache_path):
    return FewShotClassifier(examples=[], dry_run=True, cache_path=str(tmp_cache_path))


def test_dry_run_never_calls_network(tmp_path, monkeypatch):
    clf = _classifier(tmp_path / "cache.json")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("network should never be called in dry-run mode")

    monkeypatch.setattr("anthropic.Anthropic", fail_if_called, raising=False)
    result = clf.classify("FB-TEST-1", ClassifierInput(feedback_text="App crashes constantly."))
    assert result.output is not None
    assert result.dry_run is True


def test_retries_once_on_invalid_json_then_succeeds(tmp_path):
    clf = _classifier(tmp_path / "cache.json")
    calls = {"n": 0}

    def fake_call(system_prompt, user_prompt, record):
        calls["n"] += 1
        if calls["n"] == 1:
            return INVALID_JSON_TEXT, {"input_tokens": 5, "output_tokens": 5}, 0.01
        return VALID_JSON, {"input_tokens": 5, "output_tokens": 5}, 0.01

    clf._call_llm = fake_call
    result = clf.classify("FB-TEST-2", ClassifierInput(feedback_text="x"))

    assert calls["n"] == 2
    assert result.retries == 1
    assert result.output is not None
    assert result.output.feedback_type == "Bug report"


def test_retry_limit_stores_failure_instead_of_looping(tmp_path):
    clf = _classifier(tmp_path / "cache.json")
    calls = {"n": 0}

    def always_bad(system_prompt, user_prompt, record):
        calls["n"] += 1
        return INVALID_JSON_TEXT, {"input_tokens": 1, "output_tokens": 1}, 0.01

    clf._call_llm = always_bad
    result = clf.classify("FB-TEST-3", ClassifierInput(feedback_text="x"))

    assert calls["n"] == MAX_ATTEMPTS  # never loops beyond the retry limit
    assert result.output is None
    assert result.error is not None
    assert len(clf.failures) == 1
    assert clf.failures[0]["feedback_id"] == "FB-TEST-3"


def test_schema_invalid_json_triggers_retry_and_is_recorded_as_failure(tmp_path):
    clf = _classifier(tmp_path / "cache.json")

    def always_schema_invalid(system_prompt, user_prompt, record):
        return SCHEMA_INVALID_JSON, {"input_tokens": 1, "output_tokens": 1}, 0.01

    clf._call_llm = always_schema_invalid
    result = clf.classify("FB-TEST-4", ClassifierInput(feedback_text="x"))

    assert result.output is None
    assert len(clf.failures) == 1


def test_cache_hit_skips_reclassification(tmp_path):
    cache_path = tmp_path / "cache.json"
    clf = _classifier(cache_path)
    calls = {"n": 0}

    def fake_call(system_prompt, user_prompt, record):
        calls["n"] += 1
        return VALID_JSON, {"input_tokens": 1, "output_tokens": 1}, 0.01

    clf._call_llm = fake_call
    clf.classify("FB-TEST-5", ClassifierInput(feedback_text="x"))
    assert calls["n"] == 1

    result2 = clf.classify("FB-TEST-5", ClassifierInput(feedback_text="x"))
    assert calls["n"] == 1  # no second call - served from cache
    assert result2.from_cache is True


def test_force_bypasses_cache(tmp_path):
    cache_path = tmp_path / "cache.json"
    clf = _classifier(cache_path)
    calls = {"n": 0}

    def fake_call(system_prompt, user_prompt, record):
        calls["n"] += 1
        return VALID_JSON, {"input_tokens": 1, "output_tokens": 1}, 0.01

    clf._call_llm = fake_call
    clf.classify("FB-TEST-6", ClassifierInput(feedback_text="x"))
    clf.classify("FB-TEST-6", ClassifierInput(feedback_text="x"), force=True)
    assert calls["n"] == 2


def test_cache_persists_to_disk(tmp_path):
    cache_path = tmp_path / "cache.json"
    clf = _classifier(cache_path)
    clf.classify("FB-TEST-7", ClassifierInput(feedback_text="Dashboard is slow."))
    assert os.path.exists(cache_path)
    with open(cache_path) as f:
        data = json.load(f)
    assert "FB-TEST-7" in data


def test_openai_provider_selects_openai_api_key_env_var(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    clf = FewShotClassifier(examples=[], provider="openai", cache_path=str(tmp_path / "c.json"))
    assert clf.api_key == "sk-test-123"
    assert clf._api_key_env_var() == "OPENAI_API_KEY"


def test_anthropic_provider_selects_anthropic_api_key_env_var(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-123")
    clf = FewShotClassifier(examples=[], provider="anthropic", cache_path=str(tmp_path / "c.json"))
    assert clf.api_key == "sk-ant-test-123"
    assert clf._api_key_env_var() == "ANTHROPIC_API_KEY"


def test_dry_run_defaults_true_when_no_key_present(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    clf = FewShotClassifier(examples=[], provider="openai", cache_path=str(tmp_path / "c.json"))
    assert clf.dry_run is True


def test_dry_run_explicit_false_is_respected_even_with_key(tmp_path, monkeypatch):
    # Library-level behavior: an explicit dry_run=False is honored. The safety net that
    # prevents *accidental* spend from just having a key present lives in scripts/run_llm.py
    # (--live is required), not in the library constructor.
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    clf = FewShotClassifier(examples=[], provider="openai", dry_run=False, cache_path=str(tmp_path / "c.json"))
    assert clf.dry_run is False
