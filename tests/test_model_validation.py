import pytest

from mcm_solarcheck.review.model_validation import (
    ModelAcceptancePolicy, ModelValidationSummary, evaluate_model,
)


def test_representative_m3t_validation_can_pass_explicit_gate():
    summary=ModelValidationSummary(40, 10, 8, 4, True, "reviewer")
    assert summary.recall == .8
    assert summary.false_positive_rate == .1
    assert ModelAcceptancePolicy().accepts(summary) is True


@pytest.mark.parametrize("summary", [
    ModelValidationSummary(19, 10, 8, 1, True, "reviewer"),
    ModelValidationSummary(40, 4, 4, 1, True, "reviewer"),
    ModelValidationSummary(40, 10, 6, 1, True, "reviewer"),
    ModelValidationSummary(40, 10, 8, 11, True, "reviewer"),
    ModelValidationSummary(40, 10, 8, 1, False, "reviewer"),
])
def test_validation_gate_fails_closed_when_requirement_is_missing(summary):
    assert ModelAcceptancePolicy().accepts(summary) is False


def test_validation_summary_rejects_impossible_counts():
    with pytest.raises(ValueError):
        ModelValidationSummary(10, 11, 1, 0, True, "reviewer")
    with pytest.raises(ValueError):
        ModelValidationSummary(10, 5, 6, 0, True, "reviewer")


def test_validation_requires_named_human_reviewer():
    with pytest.raises(ValueError):
        ModelValidationSummary(10, 5, 4, 0, True, " ")


def test_validation_decision_explains_all_failed_conditions():
    summary=ModelValidationSummary(10, 2, 1, 4, False, "reviewer")
    decision=evaluate_model(summary)
    assert decision.accepted is False
    assert "validation imagery is not representative M3T data" in decision.reasons
    assert "insufficient validation samples" in decision.reasons
    assert "insufficient defect samples" in decision.reasons
    assert "defect recall below acceptance threshold" in decision.reasons
    assert "false-positive rate above acceptance threshold" in decision.reasons


def test_validation_decision_is_accepted_without_failure_reasons():
    decision=evaluate_model(ModelValidationSummary(40, 10, 8, 4, True, "reviewer"))
    assert decision.accepted is True
    assert decision.reasons == ()
