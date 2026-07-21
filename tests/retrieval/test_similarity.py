import numpy as np

from src.retrieval.similarity import cosine_top_k


def _unit(v):
    v = np.array(v, dtype=np.float32)
    return v / np.linalg.norm(v)


def test_self_match_excluded():
    matrix = np.stack([_unit([1, 0]), _unit([1, 0]), _unit([0, 1])])
    results = cosine_top_k(matrix[0], matrix, k=5, exclude_idx=0)
    assert all(idx != 0 for idx, _ in results)


def test_top_k_ordering_is_descending():
    matrix = np.stack([_unit([1, 0]), _unit([0.9, 0.1]), _unit([0, 1])])
    results = cosine_top_k(_unit([1, 0]), matrix, k=3)
    scores = [s for _, s in results]
    assert scores == sorted(scores, reverse=True)


def test_top_k_respects_k():
    matrix = np.stack([_unit([1, i]) for i in range(10)])
    results = cosine_top_k(_unit([1, 0]), matrix, k=3)
    assert len(results) == 3


def test_similarity_score_within_range():
    matrix = np.stack([_unit([1, 0]), _unit([-1, 0]), _unit([0, 1])])
    results = cosine_top_k(_unit([1, 0]), matrix, k=3)
    for _, score in results:
        assert -1.0 <= score <= 1.0


def test_empty_matrix_returns_empty():
    empty = np.zeros((0, 4), dtype=np.float32)
    assert cosine_top_k(_unit([1, 0, 0, 0]), empty, k=5) == []
