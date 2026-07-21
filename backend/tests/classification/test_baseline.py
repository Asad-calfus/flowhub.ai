from src.classification.baseline import classify_baseline
from src.classification.schemas import CATEGORY_MAP, ClassificationOutput, ClassifierInput


def test_baseline_returns_valid_schema():
    record = ClassifierInput(feedback_text="The app crashes every time I open a task.")
    output = classify_baseline(record)
    assert isinstance(output, ClassificationOutput)


def test_baseline_category_matches_feedback_type_mapping():
    record = ClassifierInput(feedback_text="Please add a dark mode option.")
    output = classify_baseline(record)
    assert output.category == CATEGORY_MAP[output.feedback_type]


def test_baseline_detects_bug_keywords():
    record = ClassifierInput(feedback_text="The mobile app crashes when I open a task with attachments.")
    output = classify_baseline(record)
    assert output.feedback_type == "Bug report"
    assert output.product_module == "Mobile App"


def test_baseline_detects_billing_module():
    record = ClassifierInput(feedback_text="I was charged twice on my invoice this month.")
    output = classify_baseline(record)
    assert output.product_module == "Billing"


def test_baseline_is_deterministic():
    record = ClassifierInput(feedback_text="Dashboard is very slow to load today.")
    a = classify_baseline(record)
    b = classify_baseline(record)
    assert a == b


def test_baseline_enterprise_negative_escalates_urgency():
    record = ClassifierInput(feedback_text="This is broken and unacceptable.", customer_tier="Enterprise")
    output = classify_baseline(record)
    assert output.urgency in ("High", "Medium")
