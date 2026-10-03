import pytest
from types import SimpleNamespace

from mcm_solarcheck.review.evaluation_lineage import EvaluationSet, IndependentModelEvaluation
from mcm_solarcheck.review.model_lineage import TrainedModelArtifact
from mcm_solarcheck.review.model_release import create_model_release
from mcm_solarcheck.review.model_validation import ModelValidationSummary, evaluate_model
from mcm_solarcheck.review.trained_model_validation import TrainedModelValidation
from mcm_solarcheck.review.trainer_config import YoloTrainerConfig


def test_phase8_rejects_nonrepresentative_evaluation_release():
    build=SimpleNamespace(dataset_id="d"*64,snapshot_id="s"*64)
    run=YoloTrainerConfig("ultralytics","8.3",10,640,8,42).training_run(build,preprocessing="rendered_rgb")
    summary=ModelValidationSummary(20,5,5,0,False,"validator")
    evaluation=IndependentModelEvaluation(EvaluationSet("e"*64,"v"*64,False),summary)
    validation=TrainedModelValidation(TrainedModelArtifact(run.run_id,"a"*64,"pt"),evaluate_model(summary),"validator")
    with pytest.raises(ValueError,match="validation"):
        create_model_release(validation,training_run=run,evaluation=evaluation)


def test_phase8_rejects_low_recall_even_on_representative_data():
    build=SimpleNamespace(dataset_id="d"*64,snapshot_id="s"*64)
    run=YoloTrainerConfig("ultralytics","8.3",10,640,8,42).training_run(build,preprocessing="rendered_rgb")
    summary=ModelValidationSummary(20,10,2,0,True,"validator")
    evaluation=IndependentModelEvaluation(EvaluationSet("e"*64,"v"*64,True),summary)
    decision=evaluate_model(summary)
    assert not decision.accepted
    validation=TrainedModelValidation(TrainedModelArtifact(run.run_id,"a"*64,"pt"),decision,"validator")
    with pytest.raises(ValueError,match="recall"):
        create_model_release(validation,training_run=run,evaluation=evaluation)
