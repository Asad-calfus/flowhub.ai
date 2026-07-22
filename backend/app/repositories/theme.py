from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.theme import Theme, ThemeMember


def get(db: Session, theme_id: str) -> Optional[Theme]:
    return db.get(Theme, theme_id)


def list_all(db: Session, page: int, page_size: int, workspace_id: str = "demo") -> tuple[list[Theme], int]:
    base = select(Theme).where(Theme.workspace_id == workspace_id)
    total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
    stmt = base.order_by(Theme.feedback_count.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = db.execute(stmt).scalars().all()
    return list(rows), total


def next_id(db: Session) -> str:
    last = db.execute(select(Theme.id).order_by(Theme.id.desc()).limit(1)).scalar_one_or_none()
    n = int(last.split("-")[1]) + 1 if last else 1
    return f"THM-{n:03d}"


def delete_all_for_workspace(db: Session, workspace_id: str) -> None:
    """Members cascade-delete via the Theme.members relationship. Used by
    theme_service.recompute_themes to make recomputation idempotent (a fresh full
    replacement, not an additive merge)."""
    for theme in db.execute(select(Theme).where(Theme.workspace_id == workspace_id)).scalars().all():
        db.delete(theme)
    db.flush()


def upsert(db: Session, theme: Theme) -> tuple[Theme, bool]:
    existing = get(db, theme.id)
    if existing:
        return existing, False
    db.add(theme)
    db.flush()
    return theme, True


def add_member(db: Session, member: ThemeMember) -> tuple[ThemeMember, bool]:
    stmt = select(ThemeMember).where(
        ThemeMember.theme_id == member.theme_id, ThemeMember.feedback_id == member.feedback_id
    )
    existing = db.execute(stmt).scalars().first()
    if existing:
        return existing, False
    db.add(member)
    db.flush()
    return member, True


def list_members(db: Session, theme_id: str, page: int, page_size: int) -> tuple[list[ThemeMember], int]:
    base = select(ThemeMember).where(ThemeMember.theme_id == theme_id)
    total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
    stmt = base.order_by(ThemeMember.feedback_id).offset((page - 1) * page_size).limit(page_size)
    rows = db.execute(stmt).scalars().all()
    return list(rows), total
