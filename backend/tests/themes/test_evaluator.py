from src.themes.evaluator import evaluate_clustering


def _rec(fid, theme_hint):
    return {"feedback_id": fid, "theme_hint": theme_hint}


def test_perfect_clustering_scores_maximally():
    records = [_rec("FB-1", "A"), _rec("FB-2", "A"), _rec("FB-3", "B"), _rec("FB-4", "B")]
    assignments = {"FB-1": "THM-001", "FB-2": "THM-001", "FB-3": "THM-002", "FB-4": "THM-002"}
    result = evaluate_clustering(records, assignments)
    assert result["cluster_purity"] == 1.0
    assert result["adjusted_rand_index"] == 1.0
    assert result["pairwise_precision"] == 1.0
    assert result["pairwise_recall"] == 1.0
    assert result["n_fragmented_true_themes"] == 0
    assert result["n_mixed_predicted_themes"] == 0


def test_coverage_and_unclustered_percentage():
    records = [_rec("FB-1", "A"), _rec("FB-2", ""), _rec("FB-3", ""), _rec("FB-4", "")]
    assignments = {"FB-1": "THM-001", "FB-2": None, "FB-3": None, "FB-4": None}
    result = evaluate_clustering(records, assignments)
    assert result["coverage"] == 0.25
    assert result["unclustered_percentage"] == 0.75


def test_fragmented_true_theme_detected():
    records = [_rec("FB-1", "A"), _rec("FB-2", "A"), _rec("FB-3", "A"), _rec("FB-4", "A")]
    # true theme A split across two predicted clusters with >=2 members each
    assignments = {"FB-1": "THM-001", "FB-2": "THM-001", "FB-3": "THM-002", "FB-4": "THM-002"}
    result = evaluate_clustering(records, assignments)
    assert "A" in result["fragmented_true_themes"]


def test_mixed_predicted_theme_detected():
    records = [_rec("FB-1", "A"), _rec("FB-2", "B"), _rec("FB-3", "A"), _rec("FB-4", "B")]
    # one predicted cluster with an even 2/2 split between true themes -> no majority
    assignments = {"FB-1": "THM-001", "FB-2": "THM-001", "FB-3": "THM-001", "FB-4": "THM-001"}
    result = evaluate_clustering(records, assignments)
    assert "THM-001" in result["mixed_predicted_themes"]


def test_records_without_theme_hint_are_excluded_from_pairwise_and_ari():
    records = [_rec("FB-1", "A"), _rec("FB-2", "A"), _rec("FB-3", "")]
    assignments = {"FB-1": "THM-001", "FB-2": "THM-001", "FB-3": None}
    result = evaluate_clustering(records, assignments)
    assert result["n_themed_records_evaluated"] == 2
    assert result["n_total"] == 3
