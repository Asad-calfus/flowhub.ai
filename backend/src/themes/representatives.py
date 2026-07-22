"""Representative-feedback selection via centroid similarity (not shortest-text)."""

import numpy as np


def select_representatives(member_ids: list[str], member_vecs: np.ndarray, top_n: int = 3) -> list[str]:
    """Return up to top_n member ids ranked by cosine similarity to the cluster centroid.
    Deterministic tie-break by id when scores are equal."""
    if len(member_ids) == 0:
        return []
    centroid = member_vecs.mean(axis=0)
    norm = np.linalg.norm(centroid)
    if norm > 0:
        centroid = centroid / norm
    scores = member_vecs @ centroid
    order = sorted(range(len(member_ids)), key=lambda i: (-round(float(scores[i]), 8), member_ids[i]))
    k = min(top_n, len(member_ids))
    return [member_ids[i] for i in order[:k]]
