from types import SimpleNamespace
import pytest

from mcm_solarcheck.review.trainer_config import YoloTrainerConfig


def test_yolo_trainer_config_builds_exact_lineage():
    build=SimpleNamespace(dataset_id="d"*64,snapshot_id="s"*64)
    config=YoloTrainerConfig("ultralytics","8.3.0",50,640,16,42,"cpu")
    run=config.training_run(build,preprocessing="rendered_rgb")
    assert run.dataset_id==build.dataset_id
    assert run.snapshot_id==build.snapshot_id
    assert run.trainer=="ultralytics"
    assert run.trainer_version=="8.3.0"
    assert run.parameters=={"epochs":50,"imgsz":640,"batch":16,"seed":42,"device":"cpu"}


@pytest.mark.parametrize(("field","value"),[
    ("epochs",0),("image_size",0),("batch_size",0),("seed",-1),("seed",True),
])
def test_yolo_trainer_config_rejects_invalid_numeric_values(field,value):
    values={"backend":"ultralytics","backend_version":"8.3.0","epochs":50,"image_size":640,"batch_size":16,"seed":42}
    values[field]=value
    with pytest.raises(ValueError):
        YoloTrainerConfig(**values)
