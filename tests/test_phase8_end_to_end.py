"""Phase 8 production-model acceptance gate.

This test deliberately uses controlled local doubles rather than downloading
third-party weights. It verifies lineage, independent evaluation, advisory-only
release semantics, and final human authority.
"""
from pathlib import Path
from types import SimpleNamespace

from mcm_solarcheck.domain.models import Finding
from mcm_solarcheck.review.evaluation_lineage import EvaluationSet, IndependentModelEvaluation
from mcm_solarcheck.review.findings import ReviewStatus, review_finding
from mcm_solarcheck.review.model_release import attach_release_provenance, create_model_release
from mcm_solarcheck.review.model_validation import ModelValidationSummary, evaluate_model
from mcm_solarcheck.review.trained_model_validation import TrainedModelValidation
from mcm_solarcheck.review.trainer_config import YoloTrainerConfig
from mcm_solarcheck.review.training_runner import execute_training


def test_phase8_reproducible_training_to_independent_release_to_human_review(tmp_path):
    build=SimpleNamespace(dataset_id="d"*64,snapshot_id="s"*64,path=tmp_path/"dataset.yaml")
    config=YoloTrainerConfig("ultralytics","8.3.0",50,640,16,42,"cpu")
    run=config.training_run(build,preprocessing="rendered_rgb")

    def controlled_trainer(dataset,training_run):
        assert dataset.dataset_id==build.dataset_id
        assert training_run.run_id==run.run_id
        path=tmp_path/"best.pt"; path.write_bytes(b"phase8-controlled-weights"); return path

    artifact=execute_training(build,run,trainer=controlled_trainer)
    summary=ModelValidationSummary(20,5,4,1,True,"independent-validator")
    evaluation=IndependentModelEvaluation(EvaluationSet("e"*64,"v"*64,True),summary)
    decision=evaluate_model(summary)
    assert decision.accepted
    validation=TrainedModelValidation(artifact,decision,"independent-validator")
    release=create_model_release(validation,training_run=run,evaluation=evaluation)

    finding=attach_release_provenance(
        Finding("F1","T1",10,10,module_id="M1"),
        release,dataset_id=build.dataset_id,snapshot_id=build.snapshot_id,
    )
    assert finding.reviewer_status=="unreviewed"
    assert finding.metadata["classification_evaluation_id"]==evaluation.evaluation_set.evaluation_id
    reviewed,audit=review_finding(finding,status=ReviewStatus.CONFIRMED,reviewer="human-inspector")
    assert reviewed.reviewer_status=="confirmed"
    assert reviewed.metadata["review_source"]=="human"
    assert audit.status is ReviewStatus.CONFIRMED
