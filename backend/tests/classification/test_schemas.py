import pytest
from pydantic import ValidationError

from src.classification.schemas import ClassificationOutput, ClassifierInput

VALID_OUTPUT = dict(
    feedback_type="Bug report",
    category="Technical Issue",
    product_module="Mobile App",
    sentiment="Negative",
    urgency="High",
    confidence=0.9,
    reasoning="Clear crash report.",
)


def test_valid_output_passes_schema():
    output = ClassificationOutput(**VALID_OUTPUT)
    assert output.feedback_type == "Bug report"


def test_invalid_feedback_type_rejected():
    bad = {**VALID_OUTPUT, "feedback_type": "Complaint"}  # not in taxonomy
    with pytest.raises(ValidationError):
        ClassificationOutput(**bad)


def test_invalid_sentiment_rejected():
    bad = {**VALID_OUTPUT, "sentiment": "Angry"}
    with pytest.raises(ValidationError):
        ClassificationOutput(**bad)


def test_invalid_urgency_rejected():
    bad = {**VALID_OUTPUT, "urgency": "Critical"}
    with pytest.raises(ValidationError):
        ClassificationOutput(**bad)


def test_confidence_out_of_range_rejected():
    bad = {**VALID_OUTPUT, "confidence": 1.5}
    with pytest.raises(ValidationError):
        ClassificationOutput(**bad)


def test_extra_field_rejected():
    bad = {**VALID_OUTPUT, "extra_field": "not allowed"}
    with pytest.raises(ValidationError):
        ClassificationOutput(**bad)


def test_missing_required_field_rejected():
    bad = {k: v for k, v in VALID_OUTPUT.items() if k != "reasoning"}
    with pytest.raises(ValidationError):
        ClassificationOutput(**bad)


def test_classifier_input_requires_nonempty_text():
    with pytest.raises(ValidationError):
        ClassifierInput(feedback_text="")


def test_classifier_input_rejects_out_of_range_rating():
    with pytest.raises(ValidationError):
        ClassifierInput(feedback_text="hi", rating=7)


def test_classifier_input_rejects_unknown_field():
    with pytest.raises(ValidationError):
        ClassifierInput(feedback_text="hi", sentiment="Negative")


def test_from_record_matches_source_and_tier_case_insensitively():
    record = {"feedback_text": "hi", "source": "SUPPORT TICKET", "customer_tier": "pro"}
    result = ClassifierInput.from_record(record)
    assert result.source == "Support ticket"
    assert result.customer_tier == "Pro"


def test_from_record_never_raises_on_unrecognized_source_or_tier():
    """Real-world CSVs won't match our controlled vocabulary - from_record must degrade to
    None instead of raising, since a single record's messy metadata must never crash a
    classification run (batch or single)."""
    record = {"feedback_text": "hi", "source": "web widget", "customer_tier": "gold"}
    result = ClassifierInput.from_record(record)
    assert result.source is None
    assert result.customer_tier is None


def test_from_record_never_raises_on_unparsable_rating():
    record = {"feedback_text": "hi", "rating": "not-a-number"}
    result = ClassifierInput.from_record(record)
    assert result.rating is None
