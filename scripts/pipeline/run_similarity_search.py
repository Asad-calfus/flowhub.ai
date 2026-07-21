"""Run similar-feedback search (all 150 records) and product-context matching (30 gold
records only). Deterministic, local, no LLM calls.

Usage:
    python3 scripts/pipeline/run_similarity_search.py
    python3 scripts/pipeline/run_similarity_search.py --before-only   # only match against
                                                                       # feedback created earlier
"""

import argparse
import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_embeddings import generate_all  # noqa: E402

from src.data_loader import REPO_ROOT, load_gold_records  # noqa: E402
from src.retrieval.context_retriever import retrieve_context  # noqa: E402
from src.retrieval.similarity import cosine_top_k  # noqa: E402

RESULTS_DIR = os.path.join(REPO_ROOT, "results", "retrieval")
SIMILAR_PATH = os.path.join(RESULTS_DIR, "similar_feedback_predictions.csv")
CONTEXT_PATH = os.path.join(RESULTS_DIR, "context_match_predictions.csv")


def _fmt_matches(candidates) -> str:
    return ";".join(f"{c.context_id}:{c.similarity_score:.3f}" for c in candidates)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before-only", action="store_true",
                         help="only consider feedback created strictly before the query record")
    args = parser.parse_args()

    data = generate_all()
    feedback, feedback_ids, feedback_vecs = data["feedback"]
    bugs, bug_ids, bug_vecs = data["bugs"]
    frs, fr_ids, fr_vecs = data["feature_requests"]
    releases, release_ids, release_vecs = data["releases"]
    bug_titles = [b["title"] for b in bugs]
    fr_titles = [f["title"] for f in frs]
    release_titles = release_ids  # version string doubles as the title

    os.makedirs(RESULTS_DIR, exist_ok=True)

    # --- similar feedback search: all 150 records ---
    similar_rows = []
    top5_by_id = {}
    for i, record in enumerate(feedback):
        if args.before_only:
            candidate_idx = [j for j, other in enumerate(feedback) if other["created_at"] < record["created_at"]]
            if not candidate_idx:
                top5_by_id[record["feedback_id"]] = []
                continue
            sub_matrix = feedback_vecs[candidate_idx]
            hits = cosine_top_k(feedback_vecs[i], sub_matrix, 5)
            hits = [(candidate_idx[j], score) for j, score in hits]
        else:
            hits = cosine_top_k(feedback_vecs[i], feedback_vecs, 5, exclude_idx=i)

        matches = [(feedback_ids[j], score) for j, score in hits]
        top5_by_id[record["feedback_id"]] = matches
        for rank, (mid, score) in enumerate(matches, start=1):
            matched_text = feedback[feedback_ids.index(mid)]["feedback_text"]
            similar_rows.append({
                "feedback_id": record["feedback_id"],
                "rank": rank,
                "matched_feedback_id": mid,
                "similarity_score": round(score, 4),
                "text_preview": matched_text[:80],
            })

    with open(SIMILAR_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["feedback_id", "rank", "matched_feedback_id", "similarity_score", "text_preview"])
        writer.writeheader()
        writer.writerows(similar_rows)

    # --- context matching: gold records only ---
    gold = load_gold_records()
    context_rows = []
    context_results = {}
    for record in gold:
        idx = feedback_ids.index(record["feedback_id"])
        start = time.perf_counter()
        result = retrieve_context(
            record["feedback_id"], feedback_vecs[idx],
            bug_ids, bug_titles, bug_vecs,
            fr_ids, fr_titles, fr_vecs,
            release_ids, release_titles, release_vecs,
        )
        latency = time.perf_counter() - start
        context_results[record["feedback_id"]] = result
        context_rows.append({
            "feedback_id": result.feedback_id,
            "status": result.status,
            "matched_context_id": result.matched_context_id or "",
            "bug_matches": _fmt_matches(result.bugs),
            "feature_request_matches": _fmt_matches(result.feature_requests),
            "release_matches": _fmt_matches(result.releases),
            "latency_seconds": round(latency, 5),
        })

    with open(CONTEXT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "feedback_id", "status", "matched_context_id",
            "bug_matches", "feature_request_matches", "release_matches", "latency_seconds",
        ])
        writer.writeheader()
        writer.writerows(context_rows)

    print(f"Wrote {len(similar_rows)} similar-feedback rows -> {SIMILAR_PATH}")
    print(f"Wrote {len(context_rows)} context-match rows -> {CONTEXT_PATH}")


if __name__ == "__main__":
    main()
