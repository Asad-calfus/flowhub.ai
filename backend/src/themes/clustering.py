"""Deterministic agglomerative clustering over feedback embeddings only. Functions here
take ids/vectors, never full feedback rows - label fields (theme_hint, sentiment, etc.)
structurally cannot leak into clustering because this module never sees them.
"""

import os

import numpy as np
from sklearn.cluster import AgglomerativeClustering

DISTANCE_THRESHOLD = float(os.environ.get("THEME_DISTANCE_THRESHOLD", "0.55"))
MIN_THEME_SIZE = int(os.environ.get("THEME_MIN_SIZE", "4"))


def cluster_embeddings(vectors: np.ndarray, distance_threshold: float = DISTANCE_THRESHOLD) -> np.ndarray:
    """Cosine-distance average-linkage clustering. Deterministic for fixed input -
    no randomness in agglomerative clustering."""
    n = vectors.shape[0]
    if n == 0:
        return np.zeros((0,), dtype=int)
    if n == 1:
        return np.zeros((1,), dtype=int)
    model = AgglomerativeClustering(
        n_clusters=None, metric="cosine", linkage="average", distance_threshold=distance_threshold
    )
    return model.fit_predict(vectors)


def assign_theme_ids(
    ids: list[str], vectors: np.ndarray,
    distance_threshold: float = DISTANCE_THRESHOLD, min_theme_size: int = MIN_THEME_SIZE,
) -> dict[str, str | None]:
    """Map feedback_id -> theme_id (e.g. "THM-001"), or None if unclustered (raw cluster
    too small). Theme numbering is stable: sorted by descending size, tied broken by the
    smallest member id, so re-running with the same inputs reproduces the same ids."""
    labels = cluster_embeddings(vectors, distance_threshold)
    members: dict[int, list[str]] = {}
    for rid, label in zip(ids, labels):
        members.setdefault(int(label), []).append(rid)

    valid_labels = [label for label, mids in members.items() if len(mids) >= min_theme_size]
    valid_labels.sort(key=lambda label: (-len(members[label]), min(members[label])))
    label_to_theme_id = {label: f"THM-{i + 1:03d}" for i, label in enumerate(valid_labels)}

    return {rid: label_to_theme_id.get(int(label)) for rid, label in zip(ids, labels)}
