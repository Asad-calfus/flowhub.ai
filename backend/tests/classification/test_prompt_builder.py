import pytest

from src.classification.prompt_builder import build_prompt, select_few_shot_examples
from src.classification.schemas import ClassifierInput, assert_no_leakage
from src.data_loader import load_gold_records, load_non_gold_records


def test_select_few_shot_examples_excludes_gold_records():
    non_gold = load_non_gold_records()
    gold_ids = {r["feedback_id"] for r in load_gold_records()}

    examples = select_few_shot_examples(non_gold, per_type=1)

    assert len(examples) > 0
    for example in examples:
        assert example["feedback_id"] not in gold_ids
        assert example.get("is_gold_label") != "True"


def test_select_few_shot_examples_raises_if_gold_record_in_pool():
    non_gold = load_non_gold_records()
    poisoned = non_gold + [
        {**load_gold_records()[0]}  # a real gold record snuck into the pool
    ]
    with pytest.raises(ValueError):
        select_few_shot_examples(poisoned, per_type=1)


def test_gold_and_non_gold_pools_are_disjoint():
    gold_ids = {r["feedback_id"] for r in load_gold_records()}
    non_gold_ids = {r["feedback_id"] for r in load_non_gold_records()}
    assert gold_ids.isdisjoint(non_gold_ids)


def test_build_prompt_contains_no_leakage_fields_for_target_record():
    non_gold = load_non_gold_records()
    examples = select_few_shot_examples(non_gold, per_type=1)
    target = ClassifierInput(feedback_text="The app is broken.", customer_tier="Pro")

    system_prompt, user_prompt = build_prompt(target, examples)

    # The guard itself is exercised inside build_prompt(); this just confirms it didn't raise
    # and that the leakage keys aren't literally present as JSON keys in the target section.
    assert isinstance(system_prompt, str) and isinstance(user_prompt, str)
    target_section = user_prompt.split("Classify this feedback:")[1]
    for banned in ("feedback_type", "sentiment", "urgency", "related_context_id", "theme_hint"):
        assert f'"{banned}"' not in target_section


def test_leakage_guard_rejects_payload_with_label_field():
    with pytest.raises(Exception):
        assert_no_leakage({"feedback_text": "hi", "urgency": "High"})
