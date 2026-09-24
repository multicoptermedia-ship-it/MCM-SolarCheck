import pytest
from types import SimpleNamespace

from mcm_solarcheck.domain.models import Finding
from mcm_solarcheck.review.evaluation_lineage import EvaluationSet, IndependentModelEvaluation
from mcm_solarcheck.review.model_lineage import TrainedModelArtifact
from mcm_solarcheck.review.model_release import attach_release_provenance, create_model_release
from mcm_solarcheck.review.model_validation import ModelValidationDecision, ModelValidationSummary
from mcm_solarcheck.review.trained_model_validation import TrainedModelValidation
from mcm_solarcheck.review.trainer_config import YoloTrainerConfig


def _lineage():
    build=SimpleNamespace(dataset_id="d"*64,snapshot_id="s"*64)
    run=YoloTrainerConfig("ultralytics","8.3.0",50,640,16,42).training_run(build,preprocessing="rendered_rgb")
    artifact=TrainedModelArtifact(run.run_id,"a"*64,"pt")
    validation=TrainedModelValidation(artifact,ModelValidationDecision(True,()),"validator")
    evaluation=IndependentModelEvaluation(
        EvaluationSet("e"*64,"v"*64,True),
        ModelValidationSummary(20,5,4,1,True,"validator"),
    )
    return build,run,validation,evaluation


def test_phase8_release_provenance_reaches_advisory_finding():
    build,run,validation,evaluation=_lineage()
    release=create_model_release(validation,training_run=run,evaluation=evaluation)
    finding=attach_release_provenance(Finding("F1","T1",1,1,module_id="M1"),release,dataset_id=build.dataset_id,snapshot_id=build.snapshot_id)
    assert finding.reviewer_status=="unreviewed"
    assert finding.metadata["classification_training_run_id"]==run.run_id
    assert finding.metadata["classification_evaluation_id"]==evaluation.evaluation_set.evaluation_id


def test_phase8_release_fails_closed_on_artifact_run_mismatch():
    build,run,_,evaluation=_lineage()
    validation=TrainedModelValidation(TrainedModelArtifact("x"*64,"a"*64,"pt"),ModelValidationDecision(True,()),"validator")
    with pytest.raises(ValueError,match="artifact"):
        create_model_release(validation,training_run=run,evaluation=evaluation)


def test_phase8_release_requires_complete_evaluation_pair():
    _,run,validation,evaluation=_lineage()
    with pytest.raises(ValueError,match="together"):
        create_model_release(validation,training_run=run)
    with pytest.raises(ValueError,match="together"):
        create_model_release(validation,evaluation=evaluation)
