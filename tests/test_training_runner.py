from types import SimpleNamespace
import pytest

from mcm_solarcheck.review.model_lineage import TrainingRun
from mcm_solarcheck.review.training_runner import execute_training


def test_training_runner_binds_weights_to_exact_dataset(tmp_path):
    build=SimpleNamespace(dataset_id="d"*64,snapshot_id="s"*64)
    run=TrainingRun(build.dataset_id,build.snapshot_id,"test-trainer","1","rendered_rgb",{"epochs":1,"seed":42})
    def trainer(dataset,training_run):
        path=tmp_path/"model.pt"; path.write_bytes(b"weights"); return path
    artifact=execute_training(build,run,trainer=trainer)
    assert artifact.run_id==run.run_id
    assert len(artifact.weights_sha256)==64
    assert artifact.model_format=="pt"


def test_training_runner_rejects_lineage_mismatch_before_trainer(tmp_path):
    build=SimpleNamespace(dataset_id="d"*64,snapshot_id="s"*64)
    run=TrainingRun("x"*64,build.snapshot_id,"test-trainer","1","rendered_rgb",{"seed":42})
    called=False
    def trainer(*args):
        nonlocal called; called=True
    with pytest.raises(ValueError,match="lineage"):
        execute_training(build,run,trainer=trainer)
    assert called is False


def test_training_run_requires_explicit_reproducible_seed():
    with pytest.raises(ValueError,match="seed"):
        TrainingRun("d"*64,"s"*64,"trainer","1","rendered_rgb",{"epochs":1})
    with pytest.raises(ValueError,match="seed"):
        TrainingRun("d"*64,"s"*64,"trainer","1","rendered_rgb",{"seed":True})


def test_training_run_rejects_non_json_and_non_finite_parameters():
    with pytest.raises(ValueError,match="JSON"):
        TrainingRun("d"*64,"s"*64,"trainer","1","rendered_rgb",{"seed":1,"bad":object()})
    with pytest.raises(ValueError,match="finite"):
        TrainingRun("d"*64,"s"*64,"trainer","1","rendered_rgb",{"seed":1,"loss":float("nan")})
