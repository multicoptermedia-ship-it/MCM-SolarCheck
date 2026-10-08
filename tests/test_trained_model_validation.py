import pytest
from mcm_solarcheck.review.model_lineage import TrainedModelArtifact
from mcm_solarcheck.review.model_validation import ModelValidationDecision
from mcm_solarcheck.review.trained_model_validation import TrainedModelValidation, require_trained_model_validation


def _artifact():
    return TrainedModelArtifact("r"*64,"a"*64,"pt")


def test_accepted_trained_artifact_is_releasable():
    value=TrainedModelValidation(_artifact(),ModelValidationDecision(True,()),"inspector")
    assert value.releasable is True
    require_trained_model_validation(value)


def test_rejected_trained_artifact_cannot_pass_release_gate():
    value=TrainedModelValidation(_artifact(),ModelValidationDecision(False,("recall below threshold",)),"inspector")
    assert value.releasable is False
    with pytest.raises(ValueError,match="recall below threshold"):
        require_trained_model_validation(value)


def test_validation_requires_named_evaluator():
    with pytest.raises(ValueError):
        TrainedModelValidation(_artifact(),ModelValidationDecision(True,())," ")
