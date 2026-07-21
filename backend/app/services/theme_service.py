from collections import Counter

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.theme import Theme
from app.repositories import analysis as analysis_repo
from app.repositories import feedback as feedback_repo
from app.repositories import theme as theme_repo
from app.schemas.theme import ThemeDetailOut, ThemeMemberOut


def list_themes(db: Session, page: int, page_size: int) -> tuple[list[Theme], int]:
    return theme_repo.list_all(db, page, page_size)


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
