from src.churn.scoring import CustomerRiskInputs, score_customer


def test_all_negative_recent_high_urgency_is_high_risk():
    result = score_customer(CustomerRiskInputs("C1", "Enterprise", 4, 4, 4, "Negative"))
    assert result.risk_score == 100
    assert result.risk_level == "High"


def test_suggested_action_escalates_enterprise_high_risk():
    result = score_customer(CustomerRiskInputs("C1", "Enterprise", 4, 4, 4, "Negative"))
    assert result.suggested_action == "Escalate to account manager immediately"
    assert result.reviewed is False


def test_suggested_action_for_non_enterprise_high_risk():
    result = score_customer(CustomerRiskInputs("C1", "Pro", 4, 4, 4, "Negative"))
    assert result.suggested_action == "Reach out proactively"


def test_no_feedback_is_zero_risk():
    result = score_customer(CustomerRiskInputs("C2", None, 0, 0, 0, None))
    assert result.risk_score == 0
    assert result.risk_level == "Low"


def test_all_positive_is_low_risk():
    result = score_customer(CustomerRiskInputs("C3", "Pro", 5, 0, 0, "Positive"))
    assert result.risk_score == 0
    assert result.risk_level == "Low"


def test_mixed_signals_land_in_medium_band():
    # negative_ratio=0.75, high_urgency_ratio=0.5, not-recent-negative
    # -> 0.5*0.75 + 0.3*0.5 = 0.525 -> score 52
    result = score_customer(CustomerRiskInputs("C4", "Pro", 4, 3, 2, "Neutral"))
    assert result.risk_score == 52
    assert result.risk_level == "Medium"
