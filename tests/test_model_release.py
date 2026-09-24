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


def test_release_can_bind_independent_evaluation_lineage():
    from mcm_solarcheck.review.evaluation_lineage import EvaluationSet, IndependentModelEvaluation
    from mcm_solarcheck.review.model_lineage import TrainingRun
    from mcm_solarcheck.review.model_validation import ModelValidationSummary
    run=TrainingRun("d"*64,"s"*64,"trainer","1","rendered_rgb",{"seed":42})
    artifact=TrainedModelArtifact(run.run_id,"a"*64,"pt")
    validation=TrainedModelValidation(artifact,ModelValidationDecision(True,()),"inspector")
    evaluation=IndependentModelEvaluation(EvaluationSet("e"*64,"v"*64,True),ModelValidationSummary(20,5,4,1,True,"inspector"))
    release=create_model_release(validation,training_run=run,evaluation=evaluation)
    assert release.evaluation_id==evaluation.evaluation_set.evaluation_id


def test_release_rejects_training_evaluation_leakage():
    from mcm_solarcheck.review.evaluation_lineage import EvaluationSet, IndependentModelEvaluation
    from mcm_solarcheck.review.model_lineage import TrainingRun
    from mcm_solarcheck.review.model_validation import ModelValidationSummary
    run=TrainingRun("d"*64,"s"*64,"trainer","1","rendered_rgb",{"seed":42})
    validation=TrainedModelValidation(TrainedModelArtifact(run.run_id,"a"*64,"pt"),ModelValidationDecision(True,()),"inspector")
    evaluation=IndependentModelEvaluation(EvaluationSet(run.dataset_id,"v"*64,True),ModelValidationSummary(20,5,4,1,True,"inspector"))
    with pytest.raises(ValueError,match="independent"):
        create_model_release(validation,training_run=run,evaluation=evaluation)
