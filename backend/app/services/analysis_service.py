"""Analysis service - thin wrapper around the existing classification pipeline
(src/classification/). No classifier logic is duplicated here."""

from sqlalchemy.orm import Session

from app.core.exceptions import ClassificationFailedError, ClassificationUnavailableError, NotFoundError
from app.models.analysis import AnalysisResult
from app.models.feedback import Feedback
from app.repositories import analysis as analysis_repo
from app.schemas.analysis import AnalysisRequest, BatchAnalysisRequest, BatchAnalysisResultItem
from app.services.feedback_service import get_feedback
from src.classification.baseline import classify_baseline
from src.classification.classifier import FewShotClassifier
from src.classification.prompt_builder import select_few_shot_examples
from src.classification.schemas import ClassifierInput
from src.data_loader import load_non_gold_records

_llm_classifier: FewShotClassifier | None = None


def _record_dict(feedback: Feedback) -> dict:
    return {
        "feedback_text": feedback.feedback_text,
        "source": feedback.source,
        "customer_tier": feedback.customer_tier,
        "product_version": feedback.product_version,
        "rating": feedback.rating,
        "language": feedback.language,
    }


def _get_llm_classifier() -> FewShotClassifier:
    """Lazily built and cached - the few-shot example set never changes at runtime, and
    building it re-embeds nothing (examples are plain dicts), so this is cheap to reuse."""
    global _llm_classifier
    if _llm_classifier is None:
        examples = select_few_shot_examples(load_non_gold_records(), per_type=1)
        _llm_classifier = FewShotClassifier(examples=examples)
    return _llm_classifier


def analyze_feedback(db: Session, feedback_id: str, request: AnalysisRequest) -> AnalysisResult:
    feedback = get_feedback(db, feedback_id)
    clf_input = ClassifierInput.from_record(_record_dict(feedback))

    if request.method == "baseline":
        output = classify_baseline(clf_input)
        model_name = "baseline-rule-vader"
        prompt_version = None
    else:
        classifier = _get_llm_classifier()
        # Safe-by-default: dry_run unless the request explicitly opts into --live-equivalent
        # behavior AND a provider API key is actually configured.
        classifier.dry_run = not request.live
        if request.live and not classifier.api_key:
            raise ClassificationUnavailableError(
                f"Live LLM analysis requested but no API key is configured for provider "
                f"'{classifier.provider}'."
            )
        result = classifier.classify(feedback_id, clf_input, force=request.force)
        if result.output is None:
            raise ClassificationFailedError(result.error or "Classifier returned invalid structured output.")
        output = result.output
        model_name = "dry-run-stub" if result.dry_run else f"{classifier.provider}:{classifier.model}"
        prompt_version = "v1"

    analysis = AnalysisResult(
        feedback_id=feedback_id,
        feedback_type=output.feedback_type,
        category=output.category,
        product_module=output.product_module,
        sentiment=output.sentiment,
        urgency=output.urgency,
        confidence=output.confidence,
        reasoning=output.reasoning,
        model_name=model_name,
        prompt_version=prompt_version,
    )
    analysis_repo.create(db, analysis)
    feedback.processing_status = "processed"
    db.flush()
    return analysis


def get_latest_analysis(db: Session, feedback_id: str):
    get_feedback(db, feedback_id)  # 404s if the feedback itself doesn't exist
    return analysis_repo.get_latest(db, feedback_id)


def run_batch(db: Session, request: BatchAnalysisRequest) -> list[BatchAnalysisResultItem]:
    from app.repositories.feedback import list_ids_by_status

    ids = request.feedback_ids or list_ids_by_status(db, "pending")
    results = []
    for feedback_id in ids:
        try:
            # Savepoint per item: one failure rolls back only this item's changes,
            # not the rest of the already-succeeded batch.
            with db.begin_nested():
                analyze_feedback(
                    db,
                    feedback_id,
                    AnalysisRequest(method=request.method, live=request.live, force=request.force),
                )
            results.append(BatchAnalysisResultItem(feedback_id=feedback_id, status="success"))
        except (ClassificationFailedError, ClassificationUnavailableError, NotFoundError) as exc:
            results.append(BatchAnalysisResultItem(feedback_id=feedback_id, status="failed", error=str(exc)))
    return results
