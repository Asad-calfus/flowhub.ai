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

REQUIRED_IMPORT_COLUMNS = {"feedback_text"}


def create_feedback(db: Session, payload: FeedbackCreate) -> Feedback:
    feedback = Feedback(
        id=feedback_repo.next_id(db),
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


def import_feedback_csv(db: Session, content: bytes) -> ImportSummary:
    """Bulk-create feedback from an uploaded CSV. Safe to re-run: rows carrying a
    `feedback_id` that already exists are skipped rather than duplicated."""
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidInputError("CSV must be UTF-8 encoded.") from exc

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or not REQUIRED_IMPORT_COLUMNS.issubset(reader.fieldnames):
        raise InvalidInputError(f"CSV must include columns: {sorted(REQUIRED_IMPORT_COLUMNS)}")

    summary = ImportSummary()
    for i, row in enumerate(reader, start=2):  # header is line 1
        feedback_text = (row.get("feedback_text") or "").strip()
        if not feedback_text:
            summary.errors.append(f"line {i}: missing feedback_text, skipped")
            continue

        feedback_id = (row.get("feedback_id") or "").strip() or feedback_repo.next_id(db)
        if feedback_repo.exists(db, feedback_id):
            summary.feedback_skipped += 1
            continue

        rating = (row.get("rating") or "").strip()
        feedback = Feedback(
            id=feedback_id,
            feedback_text=feedback_text,
            source=(row.get("source") or "").strip() or None,
            feedback_created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else None,
            customer_id=(row.get("customer_id") or "").strip() or None,
            customer_tier=(row.get("customer_tier") or "").strip() or None,
            product_version=(row.get("product_version") or "").strip() or None,
            rating=int(rating) if rating else None,
            language=(row.get("language") or "").strip() or None,
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
