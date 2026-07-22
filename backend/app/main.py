import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.api.router import api_router
from app.api.routes.health import root_router
from app.core.config import settings
from app.core.exceptions import (
    ClassificationFailedError,
    ClassificationUnavailableError,
    DuplicateError,
    InvalidInputError,
    InvalidTokenError,
    NotFoundError,
)
from src.data_loader import REPO_ROOT
from src.logging_utils import get_jsonl_logger

_LOGS_DIR = os.path.join(REPO_ROOT, "results", "logs")
os.makedirs(_LOGS_DIR, exist_ok=True)

app = FastAPI(title=settings.APP_NAME)

# Same JSON-Lines classification log the CLI pipeline (scripts/pipeline/run_llm.py) writes
# to - attached here too so classification runs triggered live over the API (batch or
# single) are captured in the same file, not just offline pipeline runs.
get_jsonl_logger("classification.runs", os.path.join(_LOGS_DIR, "classification_runs.jsonl"))

# App-wide log file: every HTTP request (uvicorn.access), startup/shutdown/error output
# (uvicorn/uvicorn.error), and any module-level `logging.getLogger(__name__)` call anywhere
# in the app (root) - not just classification runs. `docker compose logs backend` shows the
# same lines live but doesn't persist past container recreation; this file does.
_app_log_handler = logging.FileHandler(os.path.join(_LOGS_DIR, "app.log"), encoding="utf-8")
_app_log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
for _logger_name in ("", "uvicorn", "uvicorn.error", "uvicorn.access"):
    logging.getLogger(_logger_name).addHandler(_app_log_handler)
logging.getLogger().setLevel(logging.INFO)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(root_router)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.exception_handler(NotFoundError)
def handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(DuplicateError)
def handle_duplicate(request: Request, exc: DuplicateError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(InvalidInputError)
def handle_invalid_input(request: Request, exc: InvalidInputError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(ClassificationUnavailableError)
def handle_classification_unavailable(request: Request, exc: ClassificationUnavailableError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(InvalidTokenError)
def handle_invalid_token(request: Request, exc: InvalidTokenError) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": str(exc) or "Invalid or expired share link."})


@app.exception_handler(ClassificationFailedError)
def handle_classification_failed(request: Request, exc: ClassificationFailedError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(OperationalError)
def handle_db_connection_error(request: Request, exc: OperationalError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": "Database connection failure."})


@app.exception_handler(Exception)
def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Last-resort handler: any exception not covered above (e.g. a bad value slipping past
    validation somewhere) becomes a logged 500, not a dropped/reset connection."""
    logging.getLogger("app.error").exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})
