"""One-time backfill of the existing local-pipeline outputs (Phases 1-4) into Postgres.

Reads only files already produced by backend/scripts/{data,pipeline}/*.py - it does not
regenerate or recompute anything, and never calls an LLM. Every insert is guarded by an
existence check keyed on the same id the source file uses, so re-running is always safe.
"""

import json
import os
from datetime import datetime

import numpy as np
from sqlalchemy import select

from app.models.analysis import AnalysisResult
from app.models.context import ContextMatch, ContextRecord
from app.models.embedding import Embedding
from app.models.feedback import Feedback
from app.models.theme import Theme, ThemeMember
from app.repositories import context as context_repo
from app.repositories import embedding as embedding_repo
from app.repositories import feedback as feedback_repo
from app.repositories import theme as theme_repo
from app.schemas.feedback import ImportSummary
from src.data_loader import REPO_ROOT, load_full_dataset, read_csv
from src.retrieval.embedder import DEFAULT_MODEL as EMBEDDING_MODEL

RESULTS_DIR = os.path.join(REPO_ROOT, "results")
RETRIEVAL_CACHE_DIR = os.path.join(RESULTS_DIR, "retrieval", "cache")
THEMES_DIR = os.path.join(RESULTS_DIR, "themes")


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def _parse_date(value: str | None):
    dt = _parse_dt(value)
    return dt.date() if dt else None


def _int_or_none(value: str | None) -> int | None:
    return int(value) if value not in (None, "") else None


def _import_feedback(db, summary: ImportSummary) -> None:
    for row in load_full_dataset():
        if feedback_repo.exists(db, row["feedback_id"]):
            summary.feedback_skipped += 1
            continue
        feedback_repo.create(
            db,
            Feedback(
                id=row["feedback_id"],
                feedback_text=row["feedback_text"],
                source=row.get("source") or None,
                feedback_created_at=_parse_dt(row.get("created_at")),
                customer_id=row.get("customer_id") or None,
                customer_tier=row.get("customer_tier") or None,
                product_version=row.get("product_version") or None,
                rating=_int_or_none(row.get("rating")),
                language=row.get("language") or None,
                processing_status="pending",
            ),
        )
        summary.feedback_imported += 1


def _upsert_context(db, summary: ImportSummary, record: ContextRecord) -> None:
    _, created = context_repo.upsert_record(db, record)
    if created:
        summary.context_records_imported += 1
    else:
        summary.context_records_skipped += 1


def _import_product_modules(db, summary: ImportSummary) -> None:
    for row in read_csv(os.path.join(REPO_ROOT, "data", "context", "product_modules.csv")):
        _upsert_context(
            db,
            summary,
            ContextRecord(
                id=row["module_id"],
                context_type="product_module",
                title=row["module_name"],
                description=row.get("description"),
                product_module=row["module_name"],
                raw_metadata=row,
            ),
        )


def _load_cached_vectors(cache_name: str) -> dict[str, list[float]]:
    meta_path = os.path.join(RETRIEVAL_CACHE_DIR, f"{cache_name}.json")
    vec_path = os.path.join(RETRIEVAL_CACHE_DIR, f"{cache_name}.npy")
    if not (os.path.exists(meta_path) and os.path.exists(vec_path)):
        return {}
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    vecs = np.load(vec_path)
    return {m["id"]: vecs[i].tolist() for i, m in enumerate(meta)}


def _import_known_bugs(db, summary: ImportSummary) -> None:
    vectors = _load_cached_vectors("bugs")
    for row in read_csv(os.path.join(REPO_ROOT, "data", "context", "known_bugs.csv")):
        _upsert_context(
            db,
            summary,
            ContextRecord(
                id=row["bug_id"],
                context_type="known_bug",
                title=row["title"],
                description=row.get("description"),
                product_module=row.get("product_module"),
                status=row.get("status"),
                version_metadata={"affected_versions": row.get("affected_versions"), "priority": row.get("priority")},
                vector=vectors.get(row["bug_id"]),
                raw_metadata=row,
            ),
        )


def _import_feature_requests(db, summary: ImportSummary) -> None:
    vectors = _load_cached_vectors("feature_requests")
    for row in read_csv(os.path.join(REPO_ROOT, "data", "context", "feature_requests.csv")):
        _upsert_context(
            db,
            summary,
            ContextRecord(
                id=row["request_id"],
                context_type="feature_request",
                title=row["title"],
                description=row.get("description"),
                product_module=row.get("product_module"),
                status=row.get("status"),
                version_metadata={"roadmap_status": row.get("roadmap_status"), "request_count": row.get("request_count")},
                vector=vectors.get(row["request_id"]),
                raw_metadata=row,
            ),
        )


def _import_releases(db, summary: ImportSummary) -> None:
    vectors = _load_cached_vectors("releases")
    for row in read_csv(os.path.join(REPO_ROOT, "data", "context", "product_releases.csv")):
        _upsert_context(
            db,
            summary,
            ContextRecord(
                id=row["version"],
                context_type="release",
                title=row["version"],
                description=row.get("main_changes"),
                version_metadata={
                    "release_date": row.get("release_date"),
                    "affected_modules": row.get("affected_modules"),
                    "known_limitations": row.get("known_limitations"),
                },
                vector=vectors.get(row["version"]),
                raw_metadata=row,
            ),
        )


def _import_embeddings(db, summary: ImportSummary) -> None:
    vectors = _load_cached_vectors("feedback")
    meta_path = os.path.join(RETRIEVAL_CACHE_DIR, "feedback.json")
    if not os.path.exists(meta_path):
        return
    with open(meta_path, encoding="utf-8") as f:
        meta = {m["id"]: m["hash"] for m in json.load(f)}

    for feedback_id, vector in vectors.items():
        if embedding_repo.get(db, feedback_id) is not None:
            summary.embeddings_skipped += 1
            continue
        if not feedback_repo.exists(db, feedback_id):
            summary.errors.append(f"embedding for unknown feedback_id={feedback_id} skipped")
            continue
        embedding_repo.upsert(db, feedback_id, vector, EMBEDDING_MODEL, meta.get(feedback_id, ""))
        summary.embeddings_imported += 1


def _import_baseline_analysis(db, summary: ImportSummary) -> None:
    path = os.path.join(RESULTS_DIR, "baseline_predictions.csv")
    if not os.path.exists(path):
        return
    for row in read_csv(path):
        feedback_id = row["feedback_id"]
        if not feedback_repo.exists(db, feedback_id):
            summary.errors.append(f"analysis result for unknown feedback_id={feedback_id} skipped")
            continue
        stmt = select(AnalysisResult).filter_by(feedback_id=feedback_id, model_name="baseline-rule-vader")
        existing = db.execute(stmt).scalars().first()
        if existing:
            summary.analysis_results_skipped += 1
            continue
        db.add(
            AnalysisResult(
                feedback_id=feedback_id,
                feedback_type=row["predicted_feedback_type"],
                category=row["predicted_category"],
                product_module=row["predicted_product_module"],
                sentiment=row["predicted_sentiment"],
                urgency=row["predicted_urgency"],
                confidence=float(row["confidence"]),
                reasoning=row["reasoning"][:400],
                model_name="baseline-rule-vader",
                prompt_version=None,
            )
        )
        feedback = feedback_repo.get(db, feedback_id)
        feedback.processing_status = "processed"
        summary.analysis_results_imported += 1
    db.flush()


def _parse_match_field(value: str) -> list[tuple[str, float]]:
    if not value:
        return []
    pairs = []
    for chunk in value.split(";"):
        context_id, _, score = chunk.rpartition(":")
        if context_id:
            pairs.append((context_id, float(score)))
    return pairs


def _import_context_matches(db, summary: ImportSummary) -> None:
    path = os.path.join(RESULTS_DIR, "retrieval", "context_match_predictions.csv")
    if not os.path.exists(path):
        return
    for row in read_csv(path):
        feedback_id = row["feedback_id"]
        if not feedback_repo.exists(db, feedback_id):
            summary.errors.append(f"context match for unknown feedback_id={feedback_id} skipped")
            continue
        if context_repo.list_matches_for_feedback(db, feedback_id):
            # counted per feedback record (not per candidate row) - unlike
            # context_matches_imported below, which counts rows
            summary.context_matches_skipped += 1
            continue

        matched_context_id = row.get("matched_context_id") or None
        for match_type, field in (
            ("known_bug", "bug_matches"),
            ("feature_request", "feature_request_matches"),
            ("release", "release_matches"),
        ):
            for rank, (context_id, score) in enumerate(_parse_match_field(row.get(field, "")), start=1):
                if context_repo.get_record(db, context_id) is None:
                    summary.errors.append(f"context match references unknown context_id={context_id} skipped")
                    continue
                context_repo.create_match(
                    db,
                    ContextMatch(
                        feedback_id=feedback_id,
                        context_record_id=context_id,
                        match_type=match_type,
                        similarity_score=score,
                        rank=rank,
                        match_status="matched" if context_id == matched_context_id else "candidate",
                    ),
                )
                summary.context_matches_imported += 1


def _import_themes(db, summary: ImportSummary) -> None:
    themes_path = os.path.join(THEMES_DIR, "themes.csv")
    assignments_path = os.path.join(THEMES_DIR, "theme_assignments.csv")
    metrics_path = os.path.join(THEMES_DIR, "theme_metrics.json")
    if not os.path.exists(themes_path):
        return

    latest_trend_by_theme: dict[str, str] = {}
    if os.path.exists(metrics_path):
        with open(metrics_path, encoding="utf-8") as f:
            metrics = json.load(f)
        for t in metrics.get("themes", []):
            trends = t.get("weekly_trends") or []
            if trends:
                latest_trend_by_theme[t["theme_id"]] = trends[-1]["trend_status"]

    rep_ids_by_theme: dict[str, list[str]] = {}
    for row in read_csv(themes_path):
        rep_ids = [r for r in row["representative_feedback_ids"].split(";") if r]
        rep_ids_by_theme[row["theme_id"]] = rep_ids
        theme, created = theme_repo.upsert(
            db,
            Theme(
                id=row["theme_id"],
                name=row["name"],
                keywords=[k for k in row["keywords"].split(";") if k],
                feedback_count=int(row["size"]),
                first_seen=_parse_date(row["first_seen"]),
                last_seen=_parse_date(row["last_seen"]),
                trend_status=latest_trend_by_theme.get(row["theme_id"]),
            ),
        )
        if created:
            summary.themes_imported += 1
        else:
            summary.themes_skipped += 1

    if not os.path.exists(assignments_path):
        return
    for row in read_csv(assignments_path):
        theme_id, feedback_id = row["theme_id"], row["feedback_id"]
        if not theme_id:
            continue
        if not feedback_repo.exists(db, feedback_id):
            summary.errors.append(f"theme member for unknown feedback_id={feedback_id} skipped")
            continue
        reps = rep_ids_by_theme.get(theme_id, [])
        score = round(1.0 - 0.01 * reps.index(feedback_id), 2) if feedback_id in reps else None
        _, created = theme_repo.add_member(
            db, ThemeMember(theme_id=theme_id, feedback_id=feedback_id, membership_score=score)
        )
        if created:
            summary.theme_members_imported += 1
        else:
            summary.theme_members_skipped += 1


def run_full_import(db) -> ImportSummary:
    summary = ImportSummary()
    _import_feedback(db, summary)
    _import_product_modules(db, summary)
    _import_known_bugs(db, summary)
    _import_feature_requests(db, summary)
    _import_releases(db, summary)
    db.flush()
    _import_embeddings(db, summary)
    _import_baseline_analysis(db, summary)
    _import_context_matches(db, summary)
    _import_themes(db, summary)
    return summary
