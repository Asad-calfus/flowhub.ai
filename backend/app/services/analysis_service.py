"""Analysis service - thin wrapper around the existing classification pipeline
(src/classification/). No classifier logic is duplicated here."""

import logging
import os

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ClassificationFailedError, ClassificationUnavailableError, NotFoundError
from app.models.analysis import AnalysisResult
from app.models.correction import Correction
from app.models.feedback import Feedback
from app.repositories import analysis as analysis_repo
from app.repositories import correction as correction_repo
from app.repositories.feedback import list_ids_by_status
from app.schemas.analysis import AnalysisRequest, BatchAnalysisRequest, BatchAnalysisResultItem, CostEstimateOut
from app.schemas.correction import CorrectionRequest, CorrectionStatsOut
from app.services.feedback_service import get_feedback
from src.classification.baseline import classify_baseline
from src.classification.classifier import FewShotClassifier
from src.classification.prompt_builder import select_few_shot_examples
from src.classification.pricing import API_KEY_ENV_VARS, RECOMMENDED_MODEL, estimate_run_cost_usd
from src.classification.schemas import ClassifierInput
from src.data_loader import load_non_gold_records

_base_examples: list[dict] | None = None
_logger = logging.getLogger(__name__)


def _record_dict(feedback: Feedback) -> dict:
    return {
        "feedback_text": feedback.feedback_text,
        "source": feedback.source,
        "customer_tier": feedback.customer_tier,
        "product_version": feedback.product_version,
        "rating": feedback.rating,
        "language": feedback.language,
    }


def _get_base_examples() -> list[dict]:
    """The static few-shot pool loaded from the dataset - cached since it never changes
    at runtime. Human corrections are layered on top of this fresh on every call (see
    `_get_llm_classifier`), so they can't go stale."""
    global _base_examples
    if _base_examples is None:
        _base_examples = select_few_shot_examples(load_non_gold_records(), per_type=1)
    return _base_examples


def _correction_few_shot_examples(db: Session, workspace_id: str, limit: int = 20) -> list[dict]:
    """Turns recent human corrections into few-shot examples so the classifier stops
    repeating mistakes a human already fixed. One example per corrected feedback record,
    using its current (post-correction) classification as the target output."""
    examples = []
    seen_feedback_ids: set[str] = set()
    for corr in correction_repo.recent_examples(db, workspace_id, limit=limit):
        if corr.feedback_id in seen_feedback_ids:
            continue
        seen_feedback_ids.add(corr.feedback_id)
        feedback = db.get(Feedback, corr.feedback_id)
        latest = analysis_repo.get_latest(db, corr.feedback_id)
        if feedback is None or latest is None:
            continue
        example = {"feedback_id": feedback.id, **_record_dict(feedback)}
        for field in ("feedback_type", "category", "product_module", "sentiment", "urgency"):
            example[field] = getattr(latest, field)
        examples.append(example)
    return examples


def _get_llm_classifier(db: Session, workspace_id: str = "demo") -> FewShotClassifier:
    examples = _get_base_examples() + _correction_few_shot_examples(db, workspace_id)
    return FewShotClassifier(examples=examples)


def analyze_feedback(db: Session, feedback_id: str, request: AnalysisRequest, workspace_id: str = "demo") -> AnalysisResult:
    feedback = get_feedback(db, feedback_id)
    clf_input = ClassifierInput.from_record(_record_dict(feedback))

    if request.method == "baseline":
        output = classify_baseline(clf_input)
        model_name = "baseline-rule-vader"
        prompt_version = None
    else:
        classifier = _get_llm_classifier(db, workspace_id)
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


def correct_classification(
    db: Session, feedback_id: str, request: CorrectionRequest, workspace_id: str = "demo"
) -> Correction:
    """Records a human correction to one classification field and immediately applies it:
    writes an audit-trail `Correction` row plus a new `AnalysisResult` row (append-only,
    same convention as reprocessing) carrying the corrected value so it's reflected in the
    live classification right away. Also feeds back into the LLM classifier's few-shot
    examples on the next call - see `_correction_few_shot_examples`."""
    get_feedback(db, feedback_id)  # 404s if the feedback itself doesn't exist
    latest = analysis_repo.get_latest(db, feedback_id)
    if latest is None:
        raise NotFoundError("AnalysisResult", feedback_id)

    original_value = getattr(latest, request.field)
    correction = Correction(
        workspace_id=workspace_id,
        feedback_id=feedback_id,
        field=request.field,
        original_value=original_value,
        corrected_value=request.corrected_value,
        corrected_by=request.corrected_by,
    )
    correction_repo.create(db, correction)

    corrected = AnalysisResult(
        feedback_id=feedback_id,
        feedback_type=latest.feedback_type,
        category=latest.category,
        product_module=latest.product_module,
        sentiment=latest.sentiment,
        urgency=latest.urgency,
        confidence=1.0,
        reasoning=f"Human-corrected {request.field}.",
        model_name="human_correction",
        prompt_version=None,
    )
    setattr(corrected, request.field, request.corrected_value)
    analysis_repo.create(db, corrected)
    db.flush()
    return correction


def list_corrections(db: Session, feedback_id: str) -> list[Correction]:
    get_feedback(db, feedback_id)
    return correction_repo.list_by_feedback_id(db, feedback_id)


def get_correction_stats(db: Session, workspace_id: str = "demo") -> CorrectionStatsOut:
    total_classified = db.execute(
        select(func.count()).where(Feedback.workspace_id == workspace_id, Feedback.processing_status == "processed").select_from(Feedback)
    ).scalar_one()
    corrections_by_field = correction_repo.counts_by_field(db, workspace_id)
    total_corrected_records = correction_repo.distinct_corrected_feedback_count(db, workspace_id)
    return CorrectionStatsOut(
        total_classified=total_classified,
        total_corrected_records=total_corrected_records,
        correction_rate=round(total_corrected_records / total_classified, 4) if total_classified else 0.0,
        corrections_by_field=corrections_by_field,
    )


def run_batch(db: Session, request: BatchAnalysisRequest, workspace_id: str = "demo") -> list[BatchAnalysisResultItem]:
    ids = request.feedback_ids or list_ids_by_status(db, "pending", workspace_id)
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
                    workspace_id,
                )
            results.append(BatchAnalysisResultItem(feedback_id=feedback_id, status="success"))
        except (ClassificationFailedError, ClassificationUnavailableError, NotFoundError) as exc:
            results.append(BatchAnalysisResultItem(feedback_id=feedback_id, status="failed", error=str(exc)))
        except Exception as exc:  # noqa: BLE001 - one record's unexpected failure must never take down the batch
            _logger.exception("Unexpected error classifying %s during batch analysis", feedback_id)
            results.append(BatchAnalysisResultItem(feedback_id=feedback_id, status="failed", error=str(exc)))
    return results


def estimate_batch_cost(db: Session, workspace_id: str = "demo") -> CostEstimateOut:
    """Pre-flight cost estimate for running live LLM classification over every pending
    feedback record in the workspace - the whole backlog, not just the gold set. Mirrors
    the CLI pipeline's (`scripts/pipeline/run_llm.py`) estimate-before-spend pattern, exposed
    over the API so the dashboard can show it before a user opts into a real API call."""
    pending_count = len(list_ids_by_status(db, "pending", workspace_id))
    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()
    model = os.environ.get("LLM_MODEL") or RECOMMENDED_MODEL.get(provider, "")
    api_key_env_var = API_KEY_ENV_VARS.get(provider, "ANTHROPIC_API_KEY")
    configured = bool(os.environ.get(api_key_env_var))
    estimated_cost = estimate_run_cost_usd(model, pending_count) if pending_count else 0.0
    return CostEstimateOut(
        pending_count=pending_count,
        provider=provider,
        model=model,
        configured=configured,
        estimated_cost_usd=estimated_cost,
    )
