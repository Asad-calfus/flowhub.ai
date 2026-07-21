from src.classification.evaluator import evaluate_predictions, field_metrics


def test_field_metrics_perfect_predictions():
    y_true = ["Bug report", "Praise", "Question"]
    y_pred = ["Bug report", "Praise", "Question"]
    m = field_metrics(y_true, y_pred)
    assert m["accuracy"] == 1.0
    assert m["macro_precision"] == 1.0
    assert m["macro_recall"] == 1.0
    assert m["macro_f1"] == 1.0


def test_field_metrics_known_confusion():
    y_true = ["Bug report", "Bug report", "Praise", "Praise"]
    y_pred = ["Bug report", "Praise", "Praise", "Praise"]
    m = field_metrics(y_true, y_pred)
    # accuracy: 3/4 correct
    assert m["accuracy"] == 0.75
    # Bug report: TP=1, FP=0, FN=1 -> precision=1.0, recall=0.5
    assert m["per_class"]["Bug report"]["precision"] == 1.0
    assert m["per_class"]["Bug report"]["recall"] == 0.5
    # Praise: TP=2, FP=1, FN=0 -> precision=0.667, recall=1.0
    assert round(m["per_class"]["Praise"]["precision"], 2) == 0.67
    assert m["per_class"]["Praise"]["recall"] == 1.0


def test_confusion_matrix_shape():
    y_true = ["A", "A", "B"]
    y_pred = ["A", "B", "B"]
    m = field_metrics(y_true, y_pred)
    cm = m["confusion_matrix"]
    assert cm["A"]["A"] == 1
    assert cm["A"]["B"] == 1
    assert cm["B"]["B"] == 1


def test_evaluate_predictions_handles_missing_predictions_as_unscored():
    gold_records = [
        {"feedback_id": "FB-1", "feedback_type": "Bug report", "category": "Technical Issue",
         "product_module": "Dashboard", "sentiment": "Negative", "urgency": "High"},
        {"feedback_id": "FB-2", "feedback_type": "Praise", "category": "Positive Feedback",
         "product_module": "Dashboard", "sentiment": "Positive", "urgency": "Low"},
    ]
    predictions = {
        "FB-1": {"feedback_type": "Bug report", "category": "Technical Issue",
                 "product_module": "Dashboard", "sentiment": "Negative", "urgency": "High"},
    }
    result = evaluate_predictions(gold_records, predictions)
    assert result["scored_count"] == 1
    assert result["total_gold_count"] == 2
    assert result["unscored_feedback_ids"] == ["FB-2"]
    assert result["fields"]["feedback_type"]["accuracy"] == 1.0
