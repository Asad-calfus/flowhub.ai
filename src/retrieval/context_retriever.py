"""Deterministic similarity-threshold based context matching. No LLM, no
`related_context_id` lookup - status is derived purely from retrieved similarity scores.
"""

import os

import numpy as np

from src.retrieval.schemas import ContextCandidate, ContextMatchResult
from src.retrieval.similarity import cosine_top_k

MATCH_THRESHOLD = float(os.environ.get("CONTEXT_MATCH_THRESHOLD", "0.5"))
LOW_SIGNAL_THRESHOLD = float(os.environ.get("CONTEXT_LOW_SIGNAL_THRESHOLD", "0.35"))
TOP_K = 3


def _candidates(query_vec, matrix, ids, titles, context_type) -> list[ContextCandidate]:
    hits = cosine_top_k(query_vec, matrix, TOP_K)
    return [
        ContextCandidate(context_id=ids[i], context_type=context_type, title=titles[i], rank=rank + 1, similarity_score=score)
        for rank, (i, score) in enumerate(hits)
    ]


def retrieve_context(
    feedback_id: str,
    query_vec: np.ndarray,
    bug_ids: list[str], bug_titles: list[str], bug_matrix: np.ndarray,
    fr_ids: list[str], fr_titles: list[str], fr_matrix: np.ndarray,
    release_ids: list[str], release_titles: list[str], release_matrix: np.ndarray,
) -> ContextMatchResult:
    bugs = _candidates(query_vec, bug_matrix, bug_ids, bug_titles, "known_bug")
    frs = _candidates(query_vec, fr_matrix, fr_ids, fr_titles, "feature_request")
    releases = _candidates(query_vec, release_matrix, release_ids, release_titles, "release")

    ranked = []
    if bugs:
        ranked.append(("known_bug", bugs[0].context_id, bugs[0].similarity_score))
    if frs:
        ranked.append(("duplicate_feature_request", frs[0].context_id, frs[0].similarity_score))
    if releases:
        ranked.append(("possible_release_issue", releases[0].context_id, releases[0].similarity_score))
    ranked.sort(key=lambda c: -c[2])
    top = ranked[0] if ranked else None

    if top is None or top[2] < LOW_SIGNAL_THRESHOLD:
        status, matched = "new_untracked_issue", None
    elif top[2] >= MATCH_THRESHOLD:
        status, matched = top[0], top[1]
    else:
        status, matched = "no_confident_match", None

    return ContextMatchResult(
        feedback_id=feedback_id, status=status, matched_context_id=matched,
        bugs=bugs, feature_requests=frs, releases=releases,
    )
