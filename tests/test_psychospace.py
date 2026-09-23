from backend.main import evaluate_psychospace_state


def test_psychospace_stable_case():
    result = evaluate_psychospace_state(7.5, 7.5, 4.5, 4.5)
    assert result["risk_level"] in {"stable", "watch"}
    assert result["score"] >= 0
    assert result["score"] <= 100


def test_psychospace_critical_case():
    result = evaluate_psychospace_state(4.0, 2.5, 8.5, 9.5)
    assert result["risk_level"] == "critical"
    assert "Signe de vigilance forte" in result["summary"]
