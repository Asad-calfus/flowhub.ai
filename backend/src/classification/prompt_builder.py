"""Builds the few-shot prompt for the LLM classifier.

Few-shot examples are drawn only from non-gold records (data/is_gold_label == "False").
Gold records must never appear here - see tests/test_leakage.py::test_gold_excluded_from_examples.
"""

import json

from src.classification.schemas import (
    ALLOWED_INPUT_FIELDS,
    CATEGORY_MAP,
    ClassifierInput,
    assert_no_leakage,
)

FEEDBACK_TYPES = list(CATEGORY_MAP.keys())

SYSTEM_PROMPT = (
    "You classify customer feedback for FlowHub, a project management SaaS product. "
    "Given the feedback fields, return ONLY a JSON object with exactly these keys: "
    "feedback_type, category, product_module, sentiment, urgency, confidence, reasoning. "
    "\n\n"
    "feedback_type must be one of: Bug report, Feature request, Usability issue, "
    "Performance issue, Service complaint, Praise, Question, Other.\n"
    "category must be one of: Technical Issue, Product Feedback, Support Experience, "
    "Positive Feedback, Inquiry, Other.\n"
    "product_module must be one of: Authentication, Dashboard, Task Management, "
    "Notifications, Billing, Integrations, Reports, Mobile App.\n"
    "sentiment must be one of: Positive, Neutral, Negative, Mixed.\n"
    "urgency must be one of: Low, Medium, High.\n"
    "confidence is a number between 0 and 1.\n"
    "reasoning is one short sentence (max ~30 words).\n"
    "Return raw JSON only, no markdown fences, no extra keys, no commentary."
)


def _example_to_dict(record: dict) -> dict:
    """Extract the allowed input fields plus the gold labels for a few-shot example."""
    input_fields = {k: record.get(k, "") for k in ALLOWED_INPUT_FIELDS}
    return {
        "input": input_fields,
        "output": {
            "feedback_type": record["feedback_type"],
            "category": record["category"],
            "product_module": record["product_module"],
            "sentiment": record["sentiment"],
            "urgency": record["urgency"],
            "confidence": 0.9,
            "reasoning": "Matches labeled training example.",
        },
    }


def select_few_shot_examples(non_gold_records: list[dict], per_type: int = 1) -> list[dict]:
    """Deterministically pick `per_type` example(s) per feedback_type from non-gold records.

    Raises if any candidate is a gold record (defense in depth on top of the caller
    already filtering to non-gold records).
    """
    for record in non_gold_records:
        if record.get("is_gold_label") == "True":
            raise ValueError(f"Gold record {record.get('feedback_id')} leaked into few-shot pool")

    by_type: dict[str, list[dict]] = {t: [] for t in FEEDBACK_TYPES}
    for record in sorted(non_gold_records, key=lambda r: r["feedback_id"]):
        ftype = record.get("feedback_type")
        if ftype in by_type and len(by_type[ftype]) < per_type:
            by_type[ftype].append(record)

    examples = [rec for recs in by_type.values() for rec in recs]
    examples.sort(key=lambda r: r["feedback_id"])
    return examples


def build_user_prompt(target: ClassifierInput, examples: list[dict]) -> str:
    """Build the user-turn prompt: few-shot examples followed by the target record."""
    example_blocks = [_example_to_dict(ex) for ex in examples]

    target_payload = target.model_dump(exclude_none=False)
    assert_no_leakage(target_payload)

    parts = ["Examples:"]
    for block in example_blocks:
        parts.append(json.dumps(block, ensure_ascii=False))
    parts.append("\nClassify this feedback:")
    parts.append(json.dumps({"input": target_payload}, ensure_ascii=False))
    return "\n".join(parts)


def build_prompt(target: ClassifierInput, examples: list[dict]) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) ready to send to the LLM."""
    return SYSTEM_PROMPT, build_user_prompt(target, examples)
