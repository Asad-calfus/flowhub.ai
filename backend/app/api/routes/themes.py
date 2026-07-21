from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.schemas.common import Page
from app.schemas.feedback import FeedbackOut
from app.schemas.theme import ThemeDetailOut, ThemeOut
from app.services import theme_service

router = APIRouter(prefix="/themes", tags=["themes"])


@router.get("", response_model=Page[ThemeOut])
def list_themes(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
) -> Page[ThemeOut]:
    items, total = theme_service.list_themes(db, page, page_size)
    return Page(items=[ThemeOut.model_validate(i) for i in items], total=total, page=page, page_size=page_size)


@router.get("/{theme_id}", response_model=ThemeDetailOut)
def get_theme(theme_id: str, db: Session = Depends(get_db)) -> ThemeDetailOut:
    return theme_service.get_theme_detail(db, theme_id)


@router.get("/{theme_id}/feedback", response_model=Page[FeedbackOut])
def get_theme_feedback(
    theme_id: str,
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
) -> Page[FeedbackOut]:
    items, total = theme_service.get_theme_feedback(db, theme_id, page, page_size)
    return Page(items=[FeedbackOut.model_validate(i) for i in items], total=total, page=page, page_size=page_size)
