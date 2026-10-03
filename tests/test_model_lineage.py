from mcm_solarcheck.review.model_lineage import TrainingRun, TrainedModelArtifact
import pytest


def test_training_run_id_is_reproducible_and_parameter_sensitive():
    a=TrainingRun("d"*64,"s"*64,"ultralytics","8.3","rendered_rgb",{"epochs":50,"imgsz":640,"seed":42})
    b=TrainingRun("d"*64,"s"*64,"ultralytics","8.3","rendered_rgb",{"imgsz":640,"epochs":50,"seed":42})
    assert a.run_id==b.run_id
    c=TrainingRun("d"*64,"s"*64,"ultralytics","8.3","rendered_rgb",{"epochs":51,"imgsz":640,"seed":42})
    assert c.run_id!=a.run_id


def test_model_artifact_requires_weights_digest():
    TrainedModelArtifact("r"*64,"a"*64,"pytorch")
    with pytest.raises(ValueError):
        TrainedModelArtifact("r"*64,"not-a-digest","pytorch")
