from pathlib import Path
from types import SimpleNamespace
import pytest

from mcm_solarcheck.review.trainer_config import YoloTrainerConfig
from mcm_solarcheck.review.training_runner import execute_training
from mcm_solarcheck.review.ultralytics_training import ultralytics_trainer


class FakeModel:
    def __init__(self, root):
        self.root=Path(root)
        self.kwargs=None
    def train(self, **kwargs):
        self.kwargs=kwargs
        save=self.root/"run"; (save/"weights").mkdir(parents=True)
        (save/"weights"/"best.pt").write_bytes(b"trained")
        return SimpleNamespace(save_dir=save)


def test_ultralytics_adapter_passes_exact_recorded_parameters(tmp_path):
    build=SimpleNamespace(dataset_id="d"*64,snapshot_id="s"*64,path=tmp_path/"dataset.yaml")
    config=YoloTrainerConfig("ultralytics","8.3.0",50,640,16,42,"cpu")
    run=config.training_run(build,preprocessing="rendered_rgb")
    model=FakeModel(tmp_path)
    artifact=execute_training(build,run,trainer=ultralytics_trainer(config,model=model,output_dir=tmp_path/"runs"))
    assert model.kwargs["epochs"]==50
    assert model.kwargs["imgsz"]==640
    assert model.kwargs["batch"]==16
    assert model.kwargs["seed"]==42
    assert model.kwargs["device"]=="cpu"
    assert len(artifact.weights_sha256)==64


def test_ultralytics_adapter_rejects_run_config_drift(tmp_path):
    build=SimpleNamespace(dataset_id="d"*64,snapshot_id="s"*64)
    config=YoloTrainerConfig("ultralytics","8.3.0",50,640,16,42)
    drift=YoloTrainerConfig("ultralytics","8.3.0",51,640,16,42).training_run(build,preprocessing="rendered_rgb")
    model=FakeModel(tmp_path)
    trainer=ultralytics_trainer(config,model=model,output_dir=tmp_path/"runs")
    with pytest.raises(ValueError,match="does not match"):
        trainer(build,drift)
    assert model.kwargs is None
