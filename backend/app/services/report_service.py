"""Report service - thin wrapper around src/reports/ (aggregator, evidence_builder,
generator). No aggregation/analytics logic lives here or in the route."""

from sqlalchemy.orm import Session

from app.core.exceptions import ClassificationFailedError, ClassificationUnavailableError, NotFoundError
from app.models.report import Report
from app.repositories import report as report_repo
from app.schemas.report import ReportGenerationRequest
from src.reports import aggregator, evidence_builder, generator


def generate_report(db: Session, request: ReportGenerationRequest, workspace_id: str = "demo") -> Report:
    agg = aggregator.aggregate_period(
        db, request.start_date, request.end_date, request.product_module, request.customer_tier, workspace_id
    )
    pack = evidence_builder.build_evidence_pack(db, agg)

    if request.mode == "deterministic":
        report = generator.generate_deterministic_report(pack, request.product_module, request.customer_tier)
    else:
        live = request.mode == "live"
        llm = generator.LLMReportGenerator(dry_run=not live)
        if live and not llm.api_key:
            raise ClassificationUnavailableError(
                f"Live LLM report requested but no API key is configured for provider '{llm.provider}'."
            )
        result = llm.generate(pack, force=request.force)
        if result.narrative is None:
            raise ClassificationFailedError(result.error or "LLM report generator returned invalid structured output.")
        method = "dry_run" if llm.dry_run else "llm"
        model_name = "dry-run-stub" if llm.dry_run else f"{llm.provider}:{llm.model}"
        report = generator.assemble_report(pack, result.narrative, method, model_name, request.product_module, request.customer_tier)

    report_id = report_repo.next_id(db)
    report.report_id = report_id
    db_report = Report(
        id=report_id,
        workspace_id=workspace_id,
        start_date=agg.start_date,
        end_date=agg.end_date,
        is_all_time=agg.all_time,
        product_module_filter=request.product_module,
        customer_tier_filter=request.customer_tier,
        generation_method=report.generation_method,
        model_name=report.model_name,
        prompt_version=report.prompt_version,
        evidence_json=pack.model_dump(mode="json"),
        report_json=report.model_dump(mode="json"),
        markdown=generator.render_markdown(report),
    )
    report_repo.create(db, db_report)
    return db_report


def get_report(db: Session, report_id: str) -> Report:
    report = report_repo.get(db, report_id)
    if report is None:
        raise NotFoundError("Report", report_id)
    return report


def list_reports(db: Session, page: int, page_size: int, workspace_id: str = "demo") -> tuple[list[Report], int]:
    return report_repo.list_all(db, page, page_size, workspace_id)
