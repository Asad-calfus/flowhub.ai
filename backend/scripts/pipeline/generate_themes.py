"""Cluster all 150 feedback records into themes using cached Phase 3 embeddings.
Deterministic, local, no LLM. Clustering itself never sees theme_hint or any other
label field - only feedback_id + embedding vector.

Usage:
    python3 scripts/pipeline/generate_themes.py
    THEME_DISTANCE_THRESHOLD=0.6 THEME_MIN_SIZE=5 python3 scripts/pipeline/generate_themes.py
"""

import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_embeddings import generate_all  # noqa: E402

from src.data_loader import REPO_ROOT  # noqa: E402
from src.themes.clustering import DISTANCE_THRESHOLD, MIN_THEME_SIZE, assign_theme_ids  # noqa: E402
from src.themes.keywords import extract_theme_keywords  # noqa: E402
from src.themes.naming import build_theme_name  # noqa: E402
from src.themes.representatives import select_representatives  # noqa: E402
from src.themes.trends import compute_weekly_stats  # noqa: E402

RESULTS_DIR = os.path.join(REPO_ROOT, "results", "themes")
ASSIGNMENTS_PATH = os.path.join(RESULTS_DIR, "theme_assignments.csv")
THEMES_PATH = os.path.join(RESULTS_DIR, "themes.csv")
METRICS_PATH = os.path.join(RESULTS_DIR, "theme_metrics.json")


def _distribution(rows: list[dict], field: str) -> dict[str, float]:
    from collections import Counter
    counts = Counter(r.get(field) or "unknown" for r in rows)
    total = sum(counts.values())
    return {k: round(v / total, 4) for k, v in counts.items()} if total else {}


def build_themes(feedback: list[dict], feedback_ids: list[str], feedback_vecs, assignments: dict) -> list[dict]:
    by_theme: dict[str, list[int]] = {}
    for i, rid in enumerate(feedback_ids):
        theme_id = assignments.get(rid)
        if theme_id:
            by_theme.setdefault(theme_id, []).append(i)

    texts_by_theme = {tid: [feedback[i]["feedback_text"] for i in idxs] for tid, idxs in by_theme.items()}
    all_texts = [r["feedback_text"] for r in feedback]
    keywords_by_theme = extract_theme_keywords(texts_by_theme, all_texts)

    themes = []
    for theme_id, idxs in sorted(by_theme.items()):
        rows = [feedback[i] for i in idxs]
        ids = [feedback_ids[i] for i in idxs]
        vecs = feedback_vecs[idxs]

        module_dist = _distribution(rows, "product_module")
        dominant_module = max(module_dist, key=module_dist.get) if module_dist else None
        keywords = keywords_by_theme[theme_id]
        reps = select_representatives(ids, vecs, top_n=3)
        dates = sorted(r["created_at"] for r in rows)

        themes.append({
            "theme_id": theme_id,
            "name": build_theme_name(keywords, dominant_module),
            "size": len(rows),
            "keywords": keywords,
            "representative_feedback_ids": reps,
            "dominant_product_module": dominant_module,
            "sentiment_distribution": _distribution(rows, "sentiment"),
            "product_module_distribution": module_dist,
            "first_seen": dates[0][:10],
            "last_seen": dates[-1][:10],
            "weekly_trends": compute_weekly_stats(theme_id, rows),
        })
    return themes


def main():
    data = generate_all()
    feedback, feedback_ids, feedback_vecs = data["feedback"]

    assignments = assign_theme_ids(feedback_ids, feedback_vecs, DISTANCE_THRESHOLD, MIN_THEME_SIZE)
    themes = build_themes(feedback, feedback_ids, feedback_vecs, assignments)

    os.makedirs(RESULTS_DIR, exist_ok=True)

    with open(ASSIGNMENTS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["feedback_id", "theme_id"])
        writer.writeheader()
        for rid in feedback_ids:
            writer.writerow({"feedback_id": rid, "theme_id": assignments.get(rid) or ""})

    with open(THEMES_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "theme_id", "name", "size", "keywords", "representative_feedback_ids",
            "dominant_product_module", "sentiment_distribution", "product_module_distribution",
            "first_seen", "last_seen",
        ])
        writer.writeheader()
        for t in themes:
            writer.writerow({
                "theme_id": t["theme_id"],
                "name": t["name"],
                "size": t["size"],
                "keywords": ";".join(t["keywords"]),
                "representative_feedback_ids": ";".join(t["representative_feedback_ids"]),
                "dominant_product_module": t["dominant_product_module"] or "",
                "sentiment_distribution": json.dumps(t["sentiment_distribution"]),
                "product_module_distribution": json.dumps(t["product_module_distribution"]),
                "first_seen": t["first_seen"],
                "last_seen": t["last_seen"],
            })

    n_assigned = sum(1 for rid in feedback_ids if assignments.get(rid))
    metrics = {
        "clustering_config": {
            "method": "AgglomerativeClustering (cosine distance, average linkage)",
            "distance_threshold": DISTANCE_THRESHOLD,
            "min_theme_size": MIN_THEME_SIZE,
            "embedding_model": data["embedder"].model_name,
        },
        "n_total_records": len(feedback_ids),
        "n_themes": len(themes),
        "n_assigned": n_assigned,
        "n_unclustered": len(feedback_ids) - n_assigned,
        "themes": themes,
    }
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"Wrote {ASSIGNMENTS_PATH}")
    print(f"Wrote {THEMES_PATH}")
    print(f"Wrote {METRICS_PATH}")
    print(f"{len(themes)} themes, {n_assigned}/{len(feedback_ids)} assigned, "
          f"{len(feedback_ids) - n_assigned} unclustered")


if __name__ == "__main__":
    main()
