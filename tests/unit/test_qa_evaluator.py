from src.agents.qa_evaluator import QAEvaluator

def test_qa_evaluator_initialization():
    """Verify that the QAEvaluator can be instantiated."""
    evaluator = QAEvaluator()
    assert evaluator is not None

def test_schema_validation_missing_status():
    """Verify that the schema validation catches missing status fields."""
    evaluator = QAEvaluator()
    response = {"some": "data"}
    issues = evaluator._validate_schema(response)
    assert len(issues) > 0
    assert "Missing required field: 'status'" in issues[0]
