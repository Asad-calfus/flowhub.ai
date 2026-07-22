"""AI Copilot service: embeds the question, retrieves the nearest stored feedback in this
workspace, then hands only that retrieved evidence to `CopilotAnswerer` for wording - the
model never sees or can cite feedback outside what was actually retrieved."""

from sqlalchemy.orm import Session

from app.core.exceptions import ClassificationUnavailableError
from app.repositories import analysis as analysis_repo
from app.repositories import embedding as embedding_repo
from app.repositories import feedback as feedback_repo
from app.schemas.copilot import CopilotAnswerOut, CopilotAskRequest, CopilotSource
from app.services.embedding_service import get_embedder
from src.copilot.answerer import CopilotAnswerer

_PREVIEW_LEN = 240


def ask(db: Session, request: CopilotAskRequest, workspace_id: str = "demo") -> CopilotAnswerOut:
    embedder = get_embedder()
    query_vector = embedder.encode([request.question])[0].tolist()

    neighbors = embedding_repo.search_by_vector(db, query_vector, workspace_id, request.top_k)
    feedback_by_id = feedback_repo.get_many(db, [fid for fid, _ in neighbors])
    analysis_by_id = analysis_repo.list_by_feedback_ids(db, list(feedback_by_id))

    retrieved = []
    for feedback_id, score in neighbors:
        fb = feedback_by_id.get(feedback_id)
        if fb is None:
            continue
        analysis = analysis_by_id.get(feedback_id)
        retrieved.append(
            {
                "feedback_id": feedback_id,
                "text_preview": fb.feedback_text[:_PREVIEW_LEN],
                "sentiment": analysis.sentiment if analysis else None,
                "similarity_score": round(float(score), 4),
            }
        )

    answerer = CopilotAnswerer(dry_run=not request.live)
    if request.live and not answerer.api_key:
        raise ClassificationUnavailableError(
            f"Live copilot answer requested but no API key is configured for provider '{answerer.provider}'."
        )
    answer_text, model_name = answerer.answer(request.question, retrieved)

    return CopilotAnswerOut(
        question=request.question,
        answer=answer_text,
        model_name=model_name,
        sources=[CopilotSource(**r) for r in retrieved],
    )
