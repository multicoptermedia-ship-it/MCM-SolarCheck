import pytest
from mcm_solarcheck.review.model_lineage import TrainedModelArtifact
from mcm_solarcheck.review.model_release import create_model_release
from mcm_solarcheck.review.model_validation import ModelValidationDecision
from mcm_solarcheck.review.trained_model_validation import TrainedModelValidation


def test_release_id_binds_validated_weights_and_evaluator():
    artifact=TrainedModelArtifact("r"*64,"A"*64,"pt")
    validation=TrainedModelValidation(artifact,ModelValidationDecision(True,())," inspector ")
    a=create_model_release(validation); b=create_model_release(validation)
    assert a.release_id==b.release_id
    assert a.weights_sha256=="a"*64
    assert a.evaluator=="inspector"


def test_rejected_model_cannot_create_release():
    validation=TrainedModelValidation(TrainedModelArtifact("r"*64,"a"*64,"pt"),ModelValidationDecision(False,("failed",)),"inspector")
    with pytest.raises(ValueError,match="failed"):
        create_model_release(validation)
