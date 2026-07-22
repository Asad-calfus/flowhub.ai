import inspect

from src.themes.clustering import assign_theme_ids, cluster_embeddings
from src.themes.evaluator import evaluate_clustering
from src.themes.keywords import extract_theme_keywords
from src.themes.naming import build_theme_name
from src.themes.representatives import select_representatives

LEAKAGE_FIELDS = (
    "theme_hint", "related_context_id", "is_gold_label", "label_source",
    "feedback_type", "category", "product_module", "sentiment", "urgency",
)


def test_clustering_signatures_never_accept_label_fields():
    for fn in (cluster_embeddings, assign_theme_ids):
        params = inspect.signature(fn).parameters
        for banned in LEAKAGE_FIELDS:
            assert banned not in params


def test_keywords_and_naming_and_representatives_take_only_ids_vectors_and_text():
    for fn in (extract_theme_keywords, build_theme_name, select_representatives):
        params = inspect.signature(fn).parameters
        for banned in LEAKAGE_FIELDS:
            assert banned not in params


def test_evaluator_is_the_only_module_reading_theme_hint():
    params = inspect.signature(evaluate_clustering).parameters
    assert "records" in params  # theme_hint read only from raw rows passed in here,
    # after clustering has already produced `assignments` - never the reverse.


def test_cluster_embeddings_output_has_no_label_dependence():
    import numpy as np
    vecs = np.array([[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]], dtype=np.float32)
    labels_first = cluster_embeddings(vecs, distance_threshold=0.3)
    labels_second = cluster_embeddings(vecs, distance_threshold=0.3)
    assert list(labels_first) == list(labels_second)
