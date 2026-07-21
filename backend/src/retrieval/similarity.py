"""Cosine similarity over pre-normalized vectors (dot product) with top-k ranking."""

import numpy as np


def cosine_top_k(query_vec: np.ndarray, matrix: np.ndarray, k: int, exclude_idx: int | None = None) -> list[tuple[int, float]]:
    """Return up to k (index, score) pairs from `matrix` sorted by descending similarity
    to `query_vec`, optionally excluding one row index (e.g. self-match)."""
    if matrix.shape[0] == 0:
        return []
    scores = matrix @ query_vec
    order = np.argsort(-scores)
    results = []
    for idx in order:
        idx = int(idx)
        if exclude_idx is not None and idx == exclude_idx:
            continue
        results.append((idx, float(scores[idx])))
        if len(results) >= k:
            break
    return results
