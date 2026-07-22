"""Renders a WeeklyReport to PDF bytes - same 12 sections as `generator.render_markdown`,
built directly from the WeeklyReport object (not by converting the Markdown) so reportlab's
Paragraph/Table flowables can be used directly. Purely a rendering step: every number/word
here already exists on the `WeeklyReport` passed in - nothing is computed or reworded.
"""

import io
from xml.sax.saxutils import escape as _xml_escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.reports.schemas import WeeklyReport

_styles = getSampleStyleSheet()
_H1 = ParagraphStyle("ReportH1", parent=_styles["Heading1"], spaceAfter=10)
_H2 = ParagraphStyle("ReportH2", parent=_styles["Heading2"], spaceBefore=14, spaceAfter=6)
_BODY = _styles["BodyText"]
_EVIDENCE = ParagraphStyle("ReportEvidence", parent=_styles["BodyText"], textColor=colors.grey, fontSize=8)


def _esc(value) -> str:
    """Feedback-derived text can contain <, >, & - reportlab's Paragraph markup requires
    these escaped or it raises a parse error."""
    return _xml_escape(str(value))


def _period_label(report: WeeklyReport) -> str:
    if report.period.is_all_time:
        return f"All-time (as of {report.period.end_date})"
    return f"{report.period.start_date} to {report.period.end_date}"


def _evidence_line(evidence) -> str:
    parts = []
    if evidence.representative_feedback_ids:
        parts.append(f"feedback: {', '.join(evidence.representative_feedback_ids)}")
    if evidence.related_context_ids:
        parts.append(f"context: {', '.join(evidence.related_context_ids)}")
    if evidence.related_theme_ids:
        parts.append(f"themes: {', '.join(evidence.related_theme_ids)}")
    ref = "; ".join(parts)
    return f"Evidence ({evidence.evidence_strength}): {ref}" if ref else f"Evidence: {evidence.evidence_strength}"


def _insight_block(title: str, description: str, evidence) -> list:
    return [
        Paragraph(_esc(title), _H2),
        Paragraph(_esc(description), _BODY),
        Paragraph(_esc(_evidence_line(evidence)), _EVIDENCE),
    ]


def render_pdf(report: WeeklyReport) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    story = [Paragraph(_esc(f"Weekly Customer Feedback Report: {_period_label(report)}"), _H1)]
    if report.product_module_filter or report.customer_tier_filter:
        story.append(
            Paragraph(
                _esc(f"Filters: module={report.product_module_filter or 'all'}, tier={report.customer_tier_filter or 'all'}"),
                _EVIDENCE,
            )
        )
    story.append(Spacer(1, 8))

    story.append(Paragraph("1. Executive Summary", _H2))
    story.append(Paragraph(_esc(report.executive_summary), _BODY))

    m = report.summary_metrics
    story.append(Paragraph("2. Total Feedback Received", _H2))
    metrics_table = Table(
        [
            ["Total feedback", _esc(m.total_feedback)],
            ["By source", _esc(m.feedback_by_source)],
            ["By type", _esc(m.feedback_by_type)],
            ["Sentiment distribution", _esc(m.sentiment_distribution)],
            ["By product module", _esc(m.feedback_by_product_module)],
            ["By customer tier", _esc(m.feedback_by_customer_tier)],
            ["Average confidence", _esc(m.average_confidence)],
        ],
        colWidths=[160, 340],
    )
    metrics_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
            ]
        )
    )
    story.append(metrics_table)

    sections = [
        ("3. Top Customer Pain Points", report.top_pain_points, False),
        ("4. Growing Themes", report.growing_themes, False),
        ("5. Most Negative Product Modules", report.most_negative_modules, False),
        ("6. Frequently Requested Features", report.feature_requests, False),
        ("7. Known Bugs Receiving Additional Reports", report.known_bugs_growing, False),
        ("8. Possible Release-Related Issues", report.release_related_issues, False),
        ("9. Important Enterprise Customer Feedback", report.enterprise_feedback, False),
        ("10. New or Untracked Issues", report.new_untracked_issues, False),
        ("11. Recommended Actions", report.recommended_actions, True),
    ]
    for heading, items, is_action in sections:
        story.append(Paragraph(heading, _H2))
        if not items:
            story.append(Paragraph("None in this period.", _BODY))
            continue
        for item in items:
            title = f"[{item.priority}] {item.title}" if is_action else item.title
            story.extend(_insight_block(title, item.description, item.evidence))

    story.append(Paragraph("12. Data Limitations", _H2))
    if report.data_limitations.notes:
        for note in report.data_limitations.notes:
            story.append(Paragraph(f"- {_esc(note)}", _BODY))
    else:
        story.append(Paragraph("None noted for this period.", _BODY))

    footer = f"Generated by: {report.generation_method}"
    if report.model_name:
        footer += f" ({report.model_name})"
    if report.created_at:
        footer += f", at {report.created_at}"
    story.append(Spacer(1, 12))
    story.append(Paragraph(_esc(footer), _EVIDENCE))

    doc.build(story)
    return buffer.getvalue()
