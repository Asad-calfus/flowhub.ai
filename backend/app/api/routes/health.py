from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

# Mounted at the app root (no /api/v1 prefix) in app.main.
root_router = APIRouter(tags=["health"])


@root_router.get("/health")
def health() -> dict:
    return {"status": "ok"}


# Mounted under /api/v1 via app.api.router.
v1_router = APIRouter(tags=["health"])


@v1_router.get("/status")
def status(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
