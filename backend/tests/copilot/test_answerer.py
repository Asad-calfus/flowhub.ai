from src.copilot.answerer import CopilotAnswerer, build_deterministic_answer


def test_deterministic_answer_with_no_matches():
    assert build_deterministic_answer([]) == "No related feedback found for this question."


def test_deterministic_answer_summarizes_sentiment():
    retrieved = [
        {"feedback_id": "FB-1", "text_preview": "x", "sentiment": "Negative", "similarity_score": 0.9},
        {"feedback_id": "FB-2", "text_preview": "y", "sentiment": "Negative", "similarity_score": 0.8},
    ]
    answer = build_deterministic_answer(retrieved)
    assert "FB-1" in answer and "FB-2" in answer
    assert "Negative" in answer


def test_dry_run_defaults_true_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    answerer = CopilotAnswerer()
    assert answerer.dry_run is True

    answer, model_name = answerer.answer("anything?", [])
    assert model_name == "dry-run-stub"
