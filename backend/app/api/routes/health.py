import os

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from src.classification.pricing import API_KEY_ENV_VARS

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
    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()
    api_key_env_var = API_KEY_ENV_VARS.get(provider, "ANTHROPIC_API_KEY")
    return {
        "status": "ok",
        "database": "connected",
        # Lets the frontend offer/disable the "classify with API key" option without
        # ever exposing the key itself - only whether one is configured.
        "llm_provider": provider,
        "llm_model": os.environ.get("LLM_MODEL", ""),
        "llm_configured": bool(os.environ.get(api_key_env_var)),
    }
