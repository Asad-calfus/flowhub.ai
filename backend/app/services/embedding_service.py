"""Shared embedding helper - reuses src/retrieval/ (Embedder, text_builder) against the
`embeddings` table. Split out from retrieval_service/feedback_service so both can call it
without a circular import."""

import hashlib

from sqlalchemy.orm import Session

from app.models.feedback import Feedback
from app.repositories import embedding as embedding_repo
from src.retrieval.embedder import Embedder
from src.retrieval.text_builder import build_feedback_text

_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder


def ensure_embedding(db: Session, feedback: Feedback) -> list[float]:
    """Return the current embedding for `feedback`, (re)computing it if missing or if the
    underlying text has changed since it was last embedded."""
    embedder = get_embedder()
    text = build_feedback_text(
        {
            "feedback_text": feedback.feedback_text,
            "source": feedback.source,
            "customer_tier": feedback.customer_tier,
            "product_version": feedback.product_version,
            "language": feedback.language,
        }
    )
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

    existing = embedding_repo.get(db, feedback.id)
    if existing and existing.text_hash == text_hash:
        return list(existing.vector)

    vector = embedder.encode([text])[0].tolist()
    embedding_repo.upsert(db, feedback.id, vector, embedder.model_name, text_hash)
    return vector
