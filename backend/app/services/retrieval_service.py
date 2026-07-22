"""Retrieval service - reuses src/retrieval/ (Embedder, text_builder, cosine_top_k,
context_retriever thresholds) against embeddings/context records persisted in Postgres
via pgvector, instead of the local numpy-cache files used by the standalone pipeline."""

import logging

import numpy as np
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.context import ContextMatch
from app.repositories import context as context_repo
from app.repositories import embedding as embedding_repo
from app.repositories import feedback as feedback_repo
from app.schemas.retrieval import (
    ContextMatchOut,
    ContextMatchSummary,
    RetrievalBatchRequest,
    RetrievalBatchResultItem,
    SimilarFeedbackOut,
)
from app.services.embedding_service import ensure_embedding
from app.services.feedback_service import get_feedback
from src.retrieval.context_retriever import LOW_SIGNAL_THRESHOLD, MATCH_THRESHOLD
from src.retrieval.similarity import cosine_top_k

_logger = logging.getLogger(__name__)


def get_similar_feedback(db: Session, feedback_id: str, top_k: int) -> list[SimilarFeedbackOut]:
    feedback = get_feedback(db, feedback_id)
    vector = ensure_embedding(db, feedback)
    neighbors = embedding_repo.nearest_neighbors(db, vector, feedback_id, top_k)

    matched = feedback_repo.get_many(db, [fid for fid, _ in neighbors])
    results = []
    for rank, (matched_id, score) in enumerate(neighbors, start=1):
        matched_feedback = matched.get(matched_id)
        if matched_feedback is None:
            continue
        results.append(
            SimilarFeedbackOut(
                feedback_id=feedback_id,
                matched_feedback_id=matched_id,
                rank=rank,
                similarity_score=round(score, 4),
                text_preview=matched_feedback.feedback_text[:80],
            )
        )
    return results


def _candidates(db: Session, query_vec: np.ndarray, context_type: str, top_k: int):
    records = context_repo.list_records_by_type(db, context_type)
    records = [r for r in records if r.vector is not None]
    if not records:
        return []
    matrix = np.array([r.vector for r in records], dtype=np.float32)
    hits = cosine_top_k(query_vec, matrix, top_k)
    return [(records[i], score) for i, score in hits]


def get_context_matches(db: Session, feedback_id: str, top_k: int) -> ContextMatchSummary:
    feedback = get_feedback(db, feedback_id)
    vector = np.array(ensure_embedding(db, feedback), dtype=np.float32)

    by_type = {
        "known_bug": _candidates(db, vector, "known_bug", top_k),
        "feature_request": _candidates(db, vector, "feature_request", top_k),
        "release": _candidates(db, vector, "release", top_k),
    }

    ranked_top = []
    for context_type, hits in by_type.items():
        if hits:
            record, score = hits[0]
            ranked_top.append((context_type, record.id, score))
    ranked_top.sort(key=lambda c: -c[2])
    top = ranked_top[0] if ranked_top else None

    status_map = {"known_bug": "known_bug", "feature_request": "duplicate_feature_request", "release": "possible_release_issue"}
    if top is None or top[2] < LOW_SIGNAL_THRESHOLD:
        status, matched_context_id = "new_untracked_issue", None
    elif top[2] >= MATCH_THRESHOLD:
        status, matched_context_id = status_map[top[0]], top[1]
    else:
        status, matched_context_id = "no_confident_match", None

    context_repo.delete_matches_for_feedback(db, feedback_id)
    candidates_out = []
    for context_type, hits in by_type.items():
        for rank, (record, score) in enumerate(hits, start=1):
            match_status = "matched" if matched_context_id == record.id else "candidate"
            context_repo.create_match(
                db,
                ContextMatch(
                    feedback_id=feedback_id,
                    context_record_id=record.id,
                    match_type=context_type,
                    similarity_score=round(float(score), 4),
                    rank=rank,
                    match_status=match_status,
                ),
            )
            candidates_out.append(
                ContextMatchOut(
                    feedback_id=feedback_id,
                    context_record_id=record.id,
                    context_type=context_type,
                    title=record.title,
                    match_type=context_type,
                    similarity_score=round(float(score), 4),
                    rank=rank,
                    match_status=match_status,
                )
            )

    return ContextMatchSummary(
        feedback_id=feedback_id, status=status, matched_context_id=matched_context_id, candidates=candidates_out
    )


def run_batch(db: Session, request: RetrievalBatchRequest, workspace_id: str = "demo") -> list[RetrievalBatchResultItem]:
    """Runs context-matching for a batch of feedback, defaulting to every record in the
    workspace that has no context-match rows yet - the backlog that otherwise only gets
    processed one record at a time when someone happens to open its detail page (the gap
    that shows up as the weekly report's "not run through context-match retrieval yet"
    data limitation)."""
    ids = request.feedback_ids or context_repo.list_feedback_ids_without_matches(db, workspace_id)
    results = []
    for feedback_id in ids:
        try:
            with db.begin_nested():
                get_context_matches(db, feedback_id, request.top_k)
            results.append(RetrievalBatchResultItem(feedback_id=feedback_id, status="success"))
        except NotFoundError as exc:
            results.append(RetrievalBatchResultItem(feedback_id=feedback_id, status="failed", error=str(exc)))
        except Exception as exc:  # noqa: BLE001 - one record's failure must never break the batch
            _logger.exception("Unexpected error running context-matching for %s during batch retrieval", feedback_id)
            results.append(RetrievalBatchResultItem(feedback_id=feedback_id, status="failed", error=str(exc)))
    return results
