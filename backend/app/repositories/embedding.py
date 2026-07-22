from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.embedding import Embedding
from app.models.feedback import Feedback


def get(db: Session, feedback_id: str) -> Optional[Embedding]:
    stmt = select(Embedding).where(Embedding.feedback_id == feedback_id)
    return db.execute(stmt).scalars().first()


def upsert(db: Session, feedback_id: str, vector: list[float], embedding_model: str, text_hash: str) -> Embedding:
    existing = get(db, feedback_id)
    if existing:
        existing.vector = vector
        existing.embedding_model = embedding_model
        existing.text_hash = text_hash
        db.flush()
        return existing
    row = Embedding(feedback_id=feedback_id, vector=vector, embedding_model=embedding_model, text_hash=text_hash)
    db.add(row)
    db.flush()
    return row


def nearest_neighbors(db: Session, query_vector: list[float], exclude_feedback_id: str, top_k: int) -> list[tuple[str, float]]:
    """Returns [(feedback_id, cosine_similarity)] for the top_k nearest OTHER feedback embeddings."""
    distance = Embedding.vector.cosine_distance(query_vector)
    stmt = (
        select(Embedding.feedback_id, distance)
        .where(Embedding.feedback_id != exclude_feedback_id)
        .order_by(distance)
        .limit(top_k)
    )
    return [(fid, 1.0 - dist) for fid, dist in db.execute(stmt).all()]


def search_by_vector(db: Session, query_vector: list[float], workspace_id: str, top_k: int) -> list[tuple[str, float]]:
    """Nearest feedback to an arbitrary query vector (e.g. an embedded free-text question),
    scoped to one workspace - used by the AI copilot, which has no source feedback_id to
    exclude the way `nearest_neighbors` does."""
    distance = Embedding.vector.cosine_distance(query_vector)
    stmt = (
        select(Embedding.feedback_id, distance)
        .join(Feedback, Feedback.id == Embedding.feedback_id)
        .where(Feedback.workspace_id == workspace_id)
        .order_by(distance)
        .limit(top_k)
    )
    return [(fid, 1.0 - dist) for fid, dist in db.execute(stmt).all()]
