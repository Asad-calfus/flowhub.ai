from src.themes.naming import build_theme_name


def test_name_combines_module_and_keywords():
    name = build_theme_name(["dashboard", "load", "slow"], "Dashboard")
    assert name.lower().startswith("dashboard")
    assert "slow" in name.lower() or "load" in name.lower()


def test_name_prepends_module_when_not_implied_by_keywords():
    name = build_theme_name(["okta", "sso", "session"], "Authentication")
    assert name.startswith("Authentication")


def test_name_is_not_a_meaningless_placeholder():
    name = build_theme_name(["dark", "mode", "theme"], "Dashboard")
    assert "issue cluster" not in name.lower()
    assert len(name.split()) <= 6


def test_name_falls_back_gracefully_with_no_keywords():
    name = build_theme_name([], "Billing")
    assert name == "Billing feedback"


def test_name_falls_back_with_no_module_or_keywords():
    name = build_theme_name([], None)
    assert name == "Uncategorized feedback"
