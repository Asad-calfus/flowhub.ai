import csv
import io
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import InvalidInputError, NotFoundError
from app.models.feedback import Feedback
from app.repositories import feedback as feedback_repo
from app.schemas.feedback import FeedbackCreate, ImportSummary
from app.services.embedding_service import ensure_embedding

# Real-world CSVs won't reliably use our exact column names, so each canonical field
# accepts a handful of common aliases (matched case/whitespace-insensitively). The first
# alias found for a field wins; anything with no match is simply left blank, except
# feedback_text, which is required for a row (and the file as a whole) to import at all.
COLUMN_ALIASES: dict[str, list[str]] = {
    "feedback_id": ["feedback_id", "id"],
    "feedback_text": [
        "feedback_text", "text", "feedback", "review", "review_text", "comment",
        "comments", "message", "body", "description", "content",
    ],
    "source": ["source", "channel", "platform"],
    "created_at": ["created_at", "date", "timestamp", "created", "review_date", "submitted_at"],
    "customer_id": ["customer_id", "user_id", "customerid", "userid", "customer"],
    "customer_tier": ["customer_tier", "tier", "plan", "customer_plan", "subscription"],
    "product_version": ["product_version", "version", "app_version"],
    "rating": ["rating", "score", "stars", "star_rating"],
    "language": ["language", "lang", "locale"],
}


def _normalize_header(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def _map_columns(fieldnames: list[str]) -> dict[str, str]:
    """Canonical field name -> actual CSV header that matched it, via COLUMN_ALIASES."""
    by_normalized = {_normalize_header(fn): fn for fn in fieldnames}
    mapping: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in by_normalized:
                mapping[canonical] = by_normalized[alias]
                break
    return mapping


def _col(row: dict, column_map: dict[str, str], canonical: str) -> str:
    header = column_map.get(canonical)
    return (row.get(header) or "").strip() if header else ""


def create_feedback(db: Session, payload: FeedbackCreate, workspace_id: str = "demo") -> Feedback:
    feedback = Feedback(
        id=feedback_repo.next_id(db),
        workspace_id=workspace_id,
        feedback_text=payload.feedback_text,
        source=payload.source,
        feedback_created_at=payload.feedback_created_at,
        customer_id=payload.customer_id,
        customer_tier=payload.customer_tier,
        product_version=payload.product_version,
        rating=payload.rating,
        language=payload.language,
        processing_status="pending",
    )
    feedback_repo.create(db, feedback)
    ensure_embedding(db, feedback)
    return feedback


def get_feedback(db: Session, feedback_id: str) -> Feedback:
    feedback = feedback_repo.get(db, feedback_id)
    if feedback is None:
        raise NotFoundError("Feedback", feedback_id)
    return feedback


def delete_feedback(db: Session, feedback_id: str) -> None:
    feedback = get_feedback(db, feedback_id)
    feedback_repo.delete(db, feedback)


def import_feedback_csv(db: Session, content: bytes, workspace_id: str = "demo") -> ImportSummary:
    """Bulk-create feedback from an uploaded CSV. Column names don't need to match ours
    exactly - see COLUMN_ALIASES - only a recognizable feedback-text column is required.
    Safe to re-run: rows carrying a `feedback_id` that already exists are skipped rather
    than duplicated."""
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidInputError("CSV must be UTF-8 encoded.") from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise InvalidInputError("CSV appears to be empty (no header row).")

    column_map = _map_columns(reader.fieldnames)
    if "feedback_text" not in column_map:
        raise InvalidInputError(
            "Could not find a feedback-text column. Rename one column to 'feedback_text', "
            f"or one of: {', '.join(COLUMN_ALIASES['feedback_text'][1:])}."
        )

    summary = ImportSummary()
    for i, row in enumerate(reader, start=2):  # header is line 1
        feedback_text = _col(row, column_map, "feedback_text")
        if not feedback_text:
            summary.errors.append(f"line {i}: missing feedback_text, skipped")
            continue

        feedback_id = _col(row, column_map, "feedback_id") or feedback_repo.next_id(db)
        if feedback_repo.exists(db, feedback_id):
            summary.feedback_skipped += 1
            continue

        created_at_raw = _col(row, column_map, "created_at")
        feedback_created_at = None
        if created_at_raw:
            try:
                feedback_created_at = datetime.fromisoformat(created_at_raw)
            except ValueError:
                summary.errors.append(f"line {i}: unrecognized date '{created_at_raw}', left blank")

        rating_raw = _col(row, column_map, "rating")
        rating = None
        if rating_raw:
            try:
                rating = int(float(rating_raw))
            except ValueError:
                summary.errors.append(f"line {i}: unrecognized rating '{rating_raw}', left blank")

        feedback = Feedback(
            id=feedback_id,
            workspace_id=workspace_id,
            feedback_text=feedback_text,
            source=_col(row, column_map, "source") or None,
            feedback_created_at=feedback_created_at,
            customer_id=_col(row, column_map, "customer_id") or None,
            customer_tier=_col(row, column_map, "customer_tier") or None,
            product_version=_col(row, column_map, "product_version") or None,
            rating=rating,
            language=_col(row, column_map, "language") or None,
            processing_status="pending",
        )
        feedback_repo.create(db, feedback)
        ensure_embedding(db, feedback)
        summary.feedback_imported += 1
    return summary


def list_feedback(
    db: Session,
    *,
    page: int,
    page_size: int,
    workspace_id: str = "demo",
    source: Optional[str] = None,
    sentiment: Optional[str] = None,
    category: Optional[str] = None,
    product_module: Optional[str] = None,
    customer_tier: Optional[str] = None,
    processing_status: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> tuple[list[Feedback], int]:
    return feedback_repo.list_filtered(
        db,
        workspace_id=workspace_id,
        page=page,
        page_size=page_size,
        source=source,
        sentiment=sentiment,
        category=category,
        product_module=product_module,
        customer_tier=customer_tier,
        processing_status=processing_status,
        date_from=date_from,
        date_to=date_to,
    )
