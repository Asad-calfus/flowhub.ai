import numpy as np

import src.retrieval.context_retriever as cr


def _unit(v):
    v = np.array(v, dtype=np.float32)
    return v / np.linalg.norm(v)


def _run(query, bug_matrix, bug_ids, monkeypatch=None):
    empty = np.zeros((0, query.shape[0]), dtype=np.float32)
    return cr.retrieve_context(
        "FB-TEST", query,
        bug_ids, bug_ids, bug_matrix,
        [], [], empty,
        [], [], empty,
    )


def test_high_similarity_yields_known_bug_status(monkeypatch):
    monkeypatch.setattr(cr, "MATCH_THRESHOLD", 0.5)
    monkeypatch.setattr(cr, "LOW_SIGNAL_THRESHOLD", 0.35)
    query = _unit([1, 0])
    bug_matrix = np.stack([_unit([1, 0]), _unit([0, 1])])
    result = _run(query, bug_matrix, ["BUG-001", "BUG-002"])
    assert result.status == "known_bug"
    assert result.matched_context_id == "BUG-001"


def test_low_similarity_yields_new_untracked_issue(monkeypatch):
    monkeypatch.setattr(cr, "MATCH_THRESHOLD", 0.5)
    monkeypatch.setattr(cr, "LOW_SIGNAL_THRESHOLD", 0.35)
    query = _unit([1, 0])
    bug_matrix = np.stack([_unit([-1, 0]), _unit([0, -1])])
    result = _run(query, bug_matrix, ["BUG-001", "BUG-002"])
    assert result.status == "new_untracked_issue"
    assert result.matched_context_id is None


def test_mid_similarity_yields_no_confident_match(monkeypatch):
    monkeypatch.setattr(cr, "MATCH_THRESHOLD", 0.9)
    monkeypatch.setattr(cr, "LOW_SIGNAL_THRESHOLD", 0.1)
    query = _unit([1, 0])
    bug_matrix = np.stack([_unit([1, 1.5])])  # cosine sim ~0.55: between the two thresholds
    result = _run(query, bug_matrix, ["BUG-001"])
    assert result.status == "no_confident_match"
    assert result.matched_context_id is None


def test_returned_context_ids_are_subset_of_provided_ids():
    query = _unit([1, 0, 0])
    bug_matrix = np.stack([_unit([1, 0, 0]), _unit([0.9, 0.1, 0]), _unit([0, 1, 0])])
    bug_ids = ["BUG-001", "BUG-002", "BUG-003"]
    empty = np.zeros((0, 3), dtype=np.float32)
    result = cr.retrieve_context("FB-TEST", query, bug_ids, bug_ids, bug_matrix, [], [], empty, [], [], empty)
    assert {b.context_id for b in result.bugs} <= set(bug_ids)
