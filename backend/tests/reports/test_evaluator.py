from src.reports.evaluator import evaluate_report
from src.reports.generator import generate_deterministic_report
from tests.reports.factories import make_evidence_pack


def test_metric_correctness_true_for_deterministic_report():
    pack = make_evidence_pack()
    report = generate_deterministic_report(pack)
    evaluation = evaluate_report(report, pack)
    assert evaluation.metric_correctness is True
    assert evaluation.schema_success is True


def test_theme_and_issue_coverage_full_for_deterministic_report():
    pack = make_evidence_pack()
    report = generate_deterministic_report(pack)
    evaluation = evaluate_report(report, pack)
    assert evaluation.theme_coverage == 1.0
    assert evaluation.important_issue_coverage == 1.0


def test_recommendation_support_rate_full_when_actions_have_evidence():
    pack = make_evidence_pack()
    report = generate_deterministic_report(pack)
    evaluation = evaluate_report(report, pack)
    assert evaluation.recommendation_support_rate == 1.0


def test_unsupported_claim_detected_when_evidence_stripped():
    pack = make_evidence_pack()
    report = generate_deterministic_report(pack)
    report.top_pain_points[0].evidence.representative_feedback_ids = []
    report.top_pain_points[0].evidence.related_context_ids = []
    report.top_pain_points[0].evidence.related_theme_ids = []
    evaluation = evaluate_report(report, pack)
    assert evaluation.unsupported_claim_count >= 1


def test_evidence_traceability_flags_fabricated_feedback_id():
    pack = make_evidence_pack()
    report = generate_deterministic_report(pack)
    report.top_pain_points[0].evidence.representative_feedback_ids = ["FB-DOES-NOT-EXIST"]
    evaluation = evaluate_report(report, pack)
    assert evaluation.evidence_traceability_rate < 1.0


def test_manual_rubric_defaults_to_none_placeholders():
    pack = make_evidence_pack()
    report = generate_deterministic_report(pack)
    evaluation = evaluate_report(report, pack)
    assert set(evaluation.manual_rubric) == {"correctness", "clarity", "usefulness", "evidence_quality", "actionability"}
    assert all(v is None for v in evaluation.manual_rubric.values())
