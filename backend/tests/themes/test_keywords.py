from src.themes.keywords import extract_theme_keywords


def test_extract_theme_keywords_ranks_theme_specific_terms():
    texts_by_theme = {
        "THM-001": ["dashboard loading is so slow today", "the dashboard takes forever to load"],
        "THM-002": ["please add dark mode to the app", "dark mode would help my eyes at night"],
    }
    all_texts = texts_by_theme["THM-001"] + texts_by_theme["THM-002"]
    result = extract_theme_keywords(texts_by_theme, all_texts, top_n=5)
    assert any("dashboard" in kw or "slow" in kw or "load" in kw for kw in result["THM-001"])
    assert any("dark" in kw for kw in result["THM-002"])


def test_empty_theme_yields_no_keywords():
    result = extract_theme_keywords({"THM-001": []}, ["some background text"], top_n=5)
    assert result["THM-001"] == []


def test_keyword_extraction_is_deterministic():
    texts_by_theme = {"THM-001": ["billing invoice is confusing", "invoice shows the wrong tax amount"]}
    all_texts = texts_by_theme["THM-001"]
    a = extract_theme_keywords(texts_by_theme, all_texts, top_n=5)
    b = extract_theme_keywords(texts_by_theme, all_texts, top_n=5)
    assert a == b
