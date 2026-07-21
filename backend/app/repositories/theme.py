from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.theme import Theme, ThemeMember


def get(db: Session, theme_id: str) -> Optional[Theme]:
    return db.get(Theme, theme_id)


def list_all(db: Session, page: int, page_size: int) -> tuple[list[Theme], int]:
    total = db.execute(select(func.count()).select_from(Theme)).scalar_one()
    stmt = select(Theme).order_by(Theme.feedback_count.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = db.execute(stmt).scalars().all()
    return list(rows), total


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
