"""Generate and cache embeddings for feedback + all product context records.

Usage:
    python3 scripts/pipeline/generate_embeddings.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.data_loader import REPO_ROOT, load_full_dataset, read_csv
from src.retrieval.embedder import Embedder, encode_with_cache
from src.retrieval.text_builder import (
    build_bug_text, build_feature_request_text, build_feedback_text, build_release_text,
)

CACHE_DIR = os.path.join(REPO_ROOT, "results", "retrieval", "cache")


def context_path(*parts):
    return os.path.join(REPO_ROOT, "data", "context", *parts)


def generate_all(embedder: Embedder | None = None) -> dict:
    embedder = embedder or Embedder()

    feedback = load_full_dataset()
    bugs = read_csv(context_path("known_bugs.csv"))
    frs = read_csv(context_path("feature_requests.csv"))
    releases = read_csv(context_path("product_releases.csv"))

    feedback_ids = [r["feedback_id"] for r in feedback]
    feedback_vecs = encode_with_cache(
        embedder, feedback_ids, [build_feedback_text(r) for r in feedback], CACHE_DIR, "feedback"
    )

    bug_ids = [b["bug_id"] for b in bugs]
    bug_vecs = encode_with_cache(embedder, bug_ids, [build_bug_text(b) for b in bugs], CACHE_DIR, "bugs")

    fr_ids = [f["request_id"] for f in frs]
    fr_vecs = encode_with_cache(embedder, fr_ids, [build_feature_request_text(f) for f in frs], CACHE_DIR, "feature_requests")

    release_ids = [r["version"] for r in releases]
    release_vecs = encode_with_cache(embedder, release_ids, [build_release_text(r) for r in releases], CACHE_DIR, "releases")

    return {
        "feedback": (feedback, feedback_ids, feedback_vecs),
        "bugs": (bugs, bug_ids, bug_vecs),
        "feature_requests": (frs, fr_ids, fr_vecs),
        "releases": (releases, release_ids, release_vecs),
        "embedder": embedder,
    }


def main():
    data = generate_all()
    print(f"Model: {data['embedder'].model_name} (dim={data['embedder'].dimension})")
    for key in ("feedback", "bugs", "feature_requests", "releases"):
        _, ids, vecs = data[key]
        print(f"{key}: {len(ids)} records -> {vecs.shape}")
    print(f"Cache: {CACHE_DIR}")


if __name__ == "__main__":
    main()
