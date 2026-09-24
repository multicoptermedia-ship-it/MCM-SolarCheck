from types import SimpleNamespace
import pytest

from mcm_solarcheck.review.model_lineage import TrainingRun
from mcm_solarcheck.review.training_runner import execute_training


def test_training_runner_binds_weights_to_exact_dataset(tmp_path):
    build=SimpleNamespace(dataset_id="d"*64,snapshot_id="s"*64)
    run=TrainingRun(build.dataset_id,build.snapshot_id,"test-trainer","1","rendered_rgb",{"epochs":1})
    def trainer(dataset,training_run):
        path=tmp_path/"model.pt"; path.write_bytes(b"weights"); return path
    artifact=execute_training(build,run,trainer=trainer)
    assert artifact.run_id==run.run_id
    assert len(artifact.weights_sha256)==64
    assert artifact.model_format=="pt"


def test_training_runner_rejects_lineage_mismatch_before_trainer(tmp_path):
    build=SimpleNamespace(dataset_id="d"*64,snapshot_id="s"*64)
    run=TrainingRun("x"*64,build.snapshot_id,"test-trainer","1","rendered_rgb",{})
    called=False
    def trainer(*args):
        nonlocal called; called=True
    with pytest.raises(ValueError,match="lineage"):
        execute_training(build,run,trainer=trainer)
    assert called is False
