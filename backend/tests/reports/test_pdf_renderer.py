from reportlab.graphics.shapes import Drawing

from src.reports import pdf_renderer


def test_sentiment_pie_chart_builds_drawing_for_nonzero_data():
    drawing = pdf_renderer._sentiment_pie_chart({"Positive": 0.6, "Negative": 0.4, "Neutral": 0.0})
    assert isinstance(drawing, Drawing)


def test_sentiment_pie_chart_returns_none_for_empty_data():
    assert pdf_renderer._sentiment_pie_chart({}) is None
    assert pdf_renderer._sentiment_pie_chart({"Positive": 0.0}) is None


def test_distribution_bar_chart_builds_drawing_and_caps_bars():
    data = {f"Module{i}": i for i in range(1, 15)}
    drawing = pdf_renderer._distribution_bar_chart("Title", data, max_bars=8)
    assert isinstance(drawing, Drawing)


def test_distribution_bar_chart_returns_none_for_empty_data():
    assert pdf_renderer._distribution_bar_chart("Title", {}) is None
