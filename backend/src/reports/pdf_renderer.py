"""Renders a WeeklyReport to PDF bytes - same 12 sections as `generator.render_markdown`,
built directly from the WeeklyReport object (not by converting the Markdown) so reportlab's
Paragraph/Table flowables can be used directly. Purely a rendering step: every number/word
here already exists on the `WeeklyReport` passed in - nothing is computed or reworded.
"""

import io
from xml.sax.saxutils import escape as _xml_escape

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.reports.schemas import WeeklyReport

# Same categorical palette as frontend/components/charts/SentimentChart.tsx - keep both in
# sync so a sentiment breakdown reads identically in the web view and the PDF export.
_SENTIMENT_COLORS = {
    "Positive": colors.HexColor("#008300"),
    "Neutral": colors.HexColor("#2a78d6"),
    "Negative": colors.HexColor("#e34948"),
    "Mixed": colors.HexColor("#4a3aa7"),
}
_BAR_COLOR = colors.HexColor("#0ca678")  # matches the module-distribution bar chart on the report detail page

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


def _sentiment_pie_chart(distribution: dict) -> Drawing | None:
    """Same data as SummaryMetrics.sentiment_distribution - a fraction per sentiment
    label. Returns None (renders nothing) when there's no data, rather than an empty chart."""
    data = [(name, value) for name, value in distribution.items() if value > 0]
    if not data:
        return None

    drawing = Drawing(460, 170)
    pie = Pie()
    pie.x, pie.y = 55, 15
    pie.width = pie.height = 140
    pie.data = [value for _, value in data]
    pie.labels = [f"{name} ({value * 100:.0f}%)" for name, value in data]
    pie.slices.strokeWidth = 0.5
    pie.slices.strokeColor = colors.white
    for i, (name, _) in enumerate(data):
        pie.slices[i].fillColor = _SENTIMENT_COLORS.get(name, colors.grey)
    drawing.add(pie)
    drawing.add(String(230, 155, "Sentiment distribution", fontSize=9, fillColor=colors.grey))
    return drawing


def _distribution_bar_chart(title: str, data: dict, max_bars: int = 8) -> Drawing | None:
    """Same shape as DistributionBarChart.tsx - a labeled count per category, sorted
    descending and capped so the x-axis stays readable in a fixed-width PDF page."""
    if not data:
        return None
    items = sorted(data.items(), key=lambda kv: -kv[1])[:max_bars]

    drawing = Drawing(460, 210)
    chart = VerticalBarChart()
    chart.x, chart.y = 45, 45
    chart.width, chart.height = 400, 130
    chart.data = [[value for _, value in items]]
    chart.categoryAxis.categoryNames = [str(name) for name, _ in items]
    chart.categoryAxis.labels.angle = 30
    chart.categoryAxis.labels.dy = -12
    chart.categoryAxis.labels.dx = -4
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.textAnchor = "end"
    chart.valueAxis.valueMin = 0
    chart.valueAxis.labels.fontSize = 7
    chart.bars[0].fillColor = _BAR_COLOR
    drawing.add(chart)
    drawing.add(String(45, 195, title, fontSize=9, fillColor=colors.grey))
    return drawing


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
    story.append(Spacer(1, 10))

    sentiment_chart = _sentiment_pie_chart(m.sentiment_distribution)
    if sentiment_chart is not None:
        story.append(sentiment_chart)
    module_chart = _distribution_bar_chart("Feedback by product module", m.feedback_by_product_module)
    if module_chart is not None:
        story.append(module_chart)

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
        if heading.startswith("5.") and report.most_negative_modules:
            negative_ratios = {i.product_module: round(i.negative_ratio * 100, 1) for i in report.most_negative_modules}
            chart = _distribution_bar_chart("% negative sentiment by module", negative_ratios)
            if chart is not None:
                story.append(chart)
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
