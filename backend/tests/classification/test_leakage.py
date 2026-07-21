import pytest

from src.classification.schemas import (
    ALLOWED_INPUT_FIELDS,
    LEAKAGE_FIELDS,
    ClassifierInput,
    LeakageError,
    assert_no_leakage,
    strip_leakage_fields,
)

GOLD_LIKE_RECORD = {
    "feedback_id": "FB-0001",
    "feedback_text": "App crashes on open.",
    "source": "Support ticket",
    "customer_tier": "Pro",
    "product_version": "v2.5.0",
    "rating": "1",
    "language": "en",
    "feedback_type": "Bug report",
    "category": "Technical Issue",
    "product_module": "Mobile App",
    "sentiment": "Negative",
    "urgency": "High",
    "theme_hint": "Mobile app crashes",
    "related_context_id": "BUG-005",
    "is_gold_label": "True",
    "label_source": "Manually verified",
}


def test_strip_leakage_fields_removes_all_banned_keys():
    cleaned = strip_leakage_fields(GOLD_LIKE_RECORD)
    assert set(cleaned.keys()) <= ALLOWED_INPUT_FIELDS
    for banned in LEAKAGE_FIELDS:
        assert banned not in cleaned


def test_strip_leakage_fields_also_drops_non_leakage_non_allowed_fields():
    cleaned = strip_leakage_fields(GOLD_LIKE_RECORD)
    # feedback_id is metadata, not an allowed classifier input field, and should not pass through
    assert "feedback_id" not in cleaned


def test_assert_no_leakage_raises_on_banned_field_present():
    payload = {"feedback_text": "hi", "sentiment": "Negative"}
    with pytest.raises(LeakageError):
        assert_no_leakage(payload)


def test_assert_no_leakage_passes_on_clean_payload():
    payload = {"feedback_text": "hi", "source": "Chat"}
    assert_no_leakage(payload)  # should not raise


def test_classifier_input_from_record_never_leaks_labels():
    clf_input = ClassifierInput.from_record(GOLD_LIKE_RECORD)
    dumped = clf_input.model_dump()
    for banned in LEAKAGE_FIELDS:
        assert banned not in dumped
    assert dumped["feedback_text"] == "App crashes on open."
    assert dumped["rating"] == 1
