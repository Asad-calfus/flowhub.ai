import inspect

import pytest

from src.classification.schemas import LeakageError
from src.retrieval.context_retriever import retrieve_context
from src.retrieval.text_builder import build_feedback_text

GOLD_LIKE_RECORD = {
    "feedback_text": "App crashes on open.",
    "source": "Support ticket",
    "customer_tier": "Pro",
    "product_version": "v2.5.0",
    "language": "en",
    "feedback_type": "Bug report",
    "sentiment": "Negative",
    "urgency": "High",
    "theme_hint": "Mobile app crashes",
    "related_context_id": "BUG-005",
    "is_gold_label": "True",
    "label_source": "Manually verified",
}


def test_build_feedback_text_excludes_label_fields():
    text = build_feedback_text(GOLD_LIKE_RECORD)
    for banned in ("Bug report", "Negative", "High", "BUG-005", "Manually verified"):
        assert banned not in text


def test_build_feedback_text_calls_the_leakage_guard(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "src.retrieval.text_builder.assert_no_leakage",
        lambda payload: calls.append(payload) or (_ for _ in ()).throw(LeakageError("boom")),
    )
    with pytest.raises(LeakageError):
        build_feedback_text(GOLD_LIKE_RECORD)
    assert calls, "assert_no_leakage was never invoked"


def test_retrieve_context_signature_never_accepts_related_context_id():
    params = inspect.signature(retrieve_context).parameters
    for banned in ("related_context_id", "theme_hint", "is_gold_label", "label_source", "sentiment", "urgency"):
        assert banned not in params
