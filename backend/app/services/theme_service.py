from collections import Counter
from datetime import date

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.embedding import Embedding
from app.models.feedback import Feedback
from app.models.theme import Theme, ThemeMember
from app.repositories import analysis as analysis_repo
from app.repositories import feedback as feedback_repo
from app.repositories import theme as theme_repo
from app.schemas.theme import RecomputeThemesResponse, ThemeDetailOut, ThemeMemberOut
from src.themes.clustering import assign_theme_ids
from src.themes.keywords import extract_theme_keywords
from src.themes.naming import build_theme_name
from src.themes.representatives import select_representatives
from src.themes.trends import compute_weekly_stats


def list_themes(db: Session, page: int, page_size: int, workspace_id: str = "demo") -> tuple[list[Theme], int]:
    return theme_repo.list_all(db, page, page_size, workspace_id)


def get_theme(db: Session, theme_id: str) -> Theme:
    theme = theme_repo.get(db, theme_id)
    if theme is None:
        raise NotFoundError("Theme", theme_id)
    return theme


def get_theme_detail(db: Session, theme_id: str) -> ThemeDetailOut:
    theme = get_theme(db, theme_id)
    members, _ = theme_repo.list_members(db, theme_id, page=1, page_size=theme.feedback_count or 1000)
    member_ids = [m.feedback_id for m in members]

    analyses = analysis_repo.list_by_feedback_ids(db, member_ids)
    sentiment_counts = Counter(a.sentiment for a in analyses.values())
    total = sum(sentiment_counts.values())
    sentiment_distribution = {k: round(v / total, 4) for k, v in sentiment_counts.items()} if total else {}

    ranked_members = sorted(members, key=lambda m: (m.membership_score or 0), reverse=True)
    rep_ids = [m.feedback_id for m in ranked_members[:3]]
    rep_feedback_map = feedback_repo.get_many(db, rep_ids)
    representative_feedback = [
        {"feedback_id": fid, "feedback_text": rep_feedback_map[fid].feedback_text}
        for fid in rep_ids
        if fid in rep_feedback_map
    ]

    return ThemeDetailOut(
        id=theme.id,
        name=theme.name,
        keywords=theme.keywords or [],
        feedback_count=theme.feedback_count,
        first_seen=theme.first_seen,
        last_seen=theme.last_seen,
        trend_status=theme.trend_status,
        sentiment_distribution=sentiment_distribution,
        representative_feedback=representative_feedback,
        members=[ThemeMemberOut.model_validate(m) for m in members],
    )


def get_theme_feedback(db: Session, theme_id: str, page: int, page_size: int):
    get_theme(db, theme_id)  # 404s if missing
    members, total = theme_repo.list_members(db, theme_id, page, page_size)
    feedback_map = feedback_repo.get_many(db, [m.feedback_id for m in members])
    ordered = [feedback_map[m.feedback_id] for m in members if m.feedback_id in feedback_map]
    return ordered, total


def recompute_themes(db: Session, workspace_id: str = "demo") -> RecomputeThemesResponse:
    """Live equivalent of scripts/pipeline/generate_themes.py, fed from Postgres
    embeddings for one workspace instead of local cache files. Deterministic, local,
    no LLM - reuses the same clustering/keyword/naming/representative/trend functions
    unchanged. Replaces (not merges with) this workspace's existing themes, so clicking
    "Process" more than once is safe."""
    rows = db.execute(
        select(Feedback, Embedding.vector)
        .join(Embedding, Embedding.feedback_id == Feedback.id)
        .where(Feedback.workspace_id == workspace_id)
    ).all()

    theme_repo.delete_all_for_workspace(db, workspace_id)
    if not rows:
        db.flush()
        return RecomputeThemesResponse(themes_created=0, feedback_assigned=0, feedback_unclustered=0)

    feedback_by_id = {fb.id: fb for fb, _ in rows}
    ids = list(feedback_by_id)
    vectors = np.array([vec for _, vec in rows], dtype=float)

    local_theme_by_id = assign_theme_ids(ids, vectors)
    members_by_local_theme: dict[str, list[str]] = {}
    for fid, local_theme in local_theme_by_id.items():
        if local_theme is not None:
            members_by_local_theme.setdefault(local_theme, []).append(fid)

    all_texts = [feedback_by_id[fid].feedback_text for fid in ids]
    texts_by_local_theme = {lt: [feedback_by_id[fid].feedback_text for fid in fids] for lt, fids in members_by_local_theme.items()}
    keywords_by_local_theme = extract_theme_keywords(texts_by_local_theme, all_texts)

    analyses = analysis_repo.list_by_feedback_ids(db, ids)
    vec_by_id = {fid: vec for fid, vec in zip(ids, vectors)}

    for local_theme, member_ids in members_by_local_theme.items():
        theme_id = theme_repo.next_id(db)
        member_vecs = np.array([vec_by_id[fid] for fid in member_ids])
        modules = [analyses[fid].product_module for fid in member_ids if fid in analyses]
        dominant_module = Counter(modules).most_common(1)[0][0] if modules else None
        keywords = keywords_by_local_theme.get(local_theme, [])
        name = build_theme_name(keywords, dominant_module)

        records = [
            {
                "created_at": (feedback_by_id[fid].feedback_created_at or feedback_by_id[fid].created_at).isoformat(),
                "sentiment": analyses[fid].sentiment if fid in analyses else None,
                "customer_tier": feedback_by_id[fid].customer_tier,
                "product_module": analyses[fid].product_module if fid in analyses else None,
            }
            for fid in member_ids
        ]
        weekly = compute_weekly_stats(theme_id, records)
        trend_status = weekly[-1]["trend_status"] if weekly else None
        dates = [r["created_at"][:10] for r in records]

        db.add(
            Theme(
                id=theme_id,
                workspace_id=workspace_id,
                name=name,
                keywords=keywords,
                feedback_count=len(member_ids),
                first_seen=date.fromisoformat(min(dates)),
                last_seen=date.fromisoformat(max(dates)),
                trend_status=trend_status,
            )
        )
        # Session uses autoflush=False, so theme_repo.next_id()'s MAX(id) query would
        # not see this row on the next loop iteration without an explicit flush here -
        # every theme in the batch would otherwise be assigned the same id and collide
        # on the final flush.
        db.flush()

        rep_order = select_representatives(member_ids, member_vecs, top_n=3)
        for fid in member_ids:
            score = round(1.0 - 0.01 * rep_order.index(fid), 2) if fid in rep_order else None
            db.add(ThemeMember(theme_id=theme_id, feedback_id=fid, membership_score=score))

    db.flush()
    assigned = sum(len(v) for v in members_by_local_theme.values())
    return RecomputeThemesResponse(
        themes_created=len(members_by_local_theme),
        feedback_assigned=assigned,
        feedback_unclustered=len(ids) - assigned,
    )
