import numpy as np

from src.themes.representatives import select_representatives


def _unit(v):
    v = np.array(v, dtype=np.float32)
    return v / np.linalg.norm(v)


def test_selects_ids_closest_to_centroid_and_ties_break_by_id():
    # three near-identical vectors + one clear outlier -> outlier excluded, tie among the
    # three broken by smallest id
    ids = ["FB-3", "FB-1", "FB-2", "FB-9"]
    vecs = np.stack([_unit([1, 0]), _unit([1, 0]), _unit([1, 0]), _unit([0, 1])])
    reps = select_representatives(ids, vecs, top_n=1)
    assert reps == ["FB-1"]


def test_does_not_just_pick_by_id_order_or_list_position():
    # FB-1 (first alphabetically, first in the list) is the outlier; centroid similarity
    # should exclude it even though naive order/alphabetical picks would include it
    ids = ["FB-1", "FB-5", "FB-9"]
    vecs = np.stack([_unit([0, 1]), _unit([1, 0]), _unit([0.95, 0.05])])
    reps = select_representatives(ids, vecs, top_n=2)
    assert "FB-1" not in reps
    assert set(reps) == {"FB-5", "FB-9"}


def test_top_n_capped_at_available_members():
    ids = ["FB-1", "FB-2"]
    vecs = np.stack([_unit([1, 0]), _unit([0.9, 0.1])])
    reps = select_representatives(ids, vecs, top_n=3)
    assert len(reps) == 2


def test_empty_input():
    assert select_representatives([], np.zeros((0, 3))) == []
