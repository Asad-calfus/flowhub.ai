from src.retrieval.evaluator import evaluate_context_matches, evaluate_similar_feedback
from src.retrieval.schemas import ContextCandidate, ContextMatchResult


def _candidate(cid, score, ctype="known_bug"):
    return ContextCandidate(context_id=cid, context_type=ctype, title=cid, rank=1, similarity_score=score)


def test_recall_precision_mrr_known_example():
    gold_rows = [
        {"feedback_id": "FB-1", "related_context_id": "BUG-001"},  # true match ranked 1st -> hit
        {"feedback_id": "FB-2", "related_context_id": "BUG-002"},  # true match ranked 2nd -> recall@3 only
        {"feedback_id": "FB-3", "related_context_id": "BUG-999"},  # true match never retrieved -> miss
    ]
    results = {
        "FB-1": ContextMatchResult(feedback_id="FB-1", status="known_bug", matched_context_id="BUG-001",
                                    bugs=[_candidate("BUG-001", 0.9)], feature_requests=[]),
        "FB-2": ContextMatchResult(feedback_id="FB-2", status="known_bug", matched_context_id="BUG-010",
                                    bugs=[_candidate("BUG-010", 0.8), _candidate("BUG-002", 0.6)], feature_requests=[]),
        "FB-3": ContextMatchResult(feedback_id="FB-3", status="new_untracked_issue", matched_context_id=None,
                                    bugs=[_candidate("BUG-010", 0.3)], feature_requests=[]),
    }
    m = evaluate_context_matches(gold_rows, results)
    assert m["n_with_context"] == 3
    assert round(m["recall_at_1"], 3) == round(1 / 3, 3)
    assert round(m["recall_at_3"], 3) == round(2 / 3, 3)
    assert round(m["mrr"], 3) == round((1 + 0.5 + 0) / 3, 3)


def test_new_issue_and_false_known_rates():
    gold_rows = [
        {"feedback_id": "FB-4", "related_context_id": ""},
        {"feedback_id": "FB-5", "related_context_id": ""},
    ]
    results = {
        "FB-4": ContextMatchResult(feedback_id="FB-4", status="new_untracked_issue", matched_context_id=None),
        "FB-5": ContextMatchResult(feedback_id="FB-5", status="known_bug", matched_context_id="BUG-001",
                                    bugs=[_candidate("BUG-001", 0.9)]),
    }
    m = evaluate_context_matches(gold_rows, results)
    assert m["new_issue_detection_accuracy"] == 0.5
    assert m["false_known_issue_rate"] == 0.5


def test_same_theme_precision_recall():
    all_rows = [
        {"feedback_id": "A", "theme_hint": "t1"},
        {"feedback_id": "B", "theme_hint": "t1"},
        {"feedback_id": "C", "theme_hint": "t1"},
        {"feedback_id": "D", "theme_hint": ""},
    ]
    top5_by_id = {
        "A": [("B", 0.9), ("D", 0.5)],  # 1/2 precision, 1/2 recall (2 other members: B, C)
        "B": [("A", 0.9), ("C", 0.8)],  # 2/2 precision, 2/2 recall
        "C": [("D", 0.5)],
    }
    m = evaluate_similar_feedback(all_rows, top5_by_id)
    assert m["n_themed_records_evaluated"] == 3
    assert 0.0 < m["same_theme_precision_at_5"] <= 1.0
