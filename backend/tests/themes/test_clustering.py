import numpy as np

from src.themes.clustering import assign_theme_ids, cluster_embeddings


def _unit(v):
    v = np.array(v, dtype=np.float32)
    return v / np.linalg.norm(v)


def test_clustering_is_deterministic():
    vecs = np.stack([_unit([1, 0]), _unit([0.95, 0.05]), _unit([0, 1]), _unit([0.05, 0.95])])
    labels_a = cluster_embeddings(vecs, distance_threshold=0.1)
    labels_b = cluster_embeddings(vecs, distance_threshold=0.1)
    assert list(labels_a) == list(labels_b)


def test_valid_cluster_assignments_are_subset_of_input_ids():
    ids = ["FB-1", "FB-2", "FB-3", "FB-4"]
    vecs = np.stack([_unit([1, 0]), _unit([0.95, 0.05]), _unit([0, 1]), _unit([0.05, 0.95])])
    assignments = assign_theme_ids(ids, vecs, distance_threshold=0.1, min_theme_size=2)
    assert set(assignments.keys()) == set(ids)
    for theme_id in assignments.values():
        assert theme_id is None or theme_id.startswith("THM-")


def test_small_clusters_below_min_size_are_unclustered():
    ids = ["FB-1", "FB-2", "FB-3"]
    # three mutually distant vectors -> three singleton clusters
    vecs = np.stack([_unit([1, 0, 0]), _unit([0, 1, 0]), _unit([0, 0, 1])])
    assignments = assign_theme_ids(ids, vecs, distance_threshold=0.1, min_theme_size=2)
    assert all(theme_id is None for theme_id in assignments.values())


def test_min_theme_size_boundary():
    ids = ["FB-1", "FB-2", "FB-3"]
    vecs = np.stack([_unit([1, 0]), _unit([0.99, 0.01]), _unit([0.98, 0.02])])
    tight_assignments = assign_theme_ids(ids, vecs, distance_threshold=0.2, min_theme_size=3)
    assert all(theme_id is not None for theme_id in tight_assignments.values())
    strict_assignments = assign_theme_ids(ids, vecs, distance_threshold=0.2, min_theme_size=4)
    assert all(theme_id is None for theme_id in strict_assignments.values())


def test_theme_numbering_is_stable_across_runs():
    ids = ["FB-A", "FB-B", "FB-C", "FB-D", "FB-E", "FB-F"]
    vecs = np.stack([
        _unit([1, 0]), _unit([0.98, 0.02]), _unit([0.97, 0.03]),
        _unit([0, 1]), _unit([0.02, 0.98]),
        _unit([-1, 0]),
    ])
    a = assign_theme_ids(ids, vecs, distance_threshold=0.15, min_theme_size=2)
    b = assign_theme_ids(list(reversed(ids)), vecs[::-1].copy(), distance_threshold=0.15, min_theme_size=2)
    assert a["FB-A"] == b["FB-A"]
    assert a["FB-D"] == b["FB-D"]


def test_empty_and_single_record_inputs():
    assert list(cluster_embeddings(np.zeros((0, 3)))) == []
    assert list(cluster_embeddings(np.array([[1.0, 0.0, 0.0]]))) == [0]
