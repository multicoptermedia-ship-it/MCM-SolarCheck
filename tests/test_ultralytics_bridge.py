import pytest

from mcm_solarcheck.review.ultralytics_bridge import detections_from_ultralytics, infer_ultralytics


class _Tensor:
    def __init__(self, value):
        self.value=value
    def detach(self):
        return self
    def cpu(self):
        return self
    def tolist(self):
        return self.value


class _Boxes:
    def __init__(self, cls, conf, xyxy):
        self.cls=_Tensor(cls)
        self.conf=_Tensor(conf)
        self.xyxy=_Tensor(xyxy)


class _Result:
    names={0: "normal", 1: "hotspot"}
    boxes=_Boxes([1], [.88], [[1, 2, 30, 40]])


def test_ultralytics_result_is_translated_without_runtime_import():
    detections=detections_from_ultralytics(_Result())
    assert len(detections) == 1
    assert detections[0].class_name == "hotspot"
    assert detections[0].confidence == .88
    assert detections[0].box_xyxy == (1.0, 2.0, 30.0, 40.0)


def test_ultralytics_bridge_rejects_unknown_class_id():
    result=_Result()
    result.boxes=_Boxes([9], [.8], [[1, 2, 3, 4]])
    with pytest.raises(ValueError):
        detections_from_ultralytics(result)


def test_ultralytics_bridge_rejects_misaligned_box_fields():
    result=_Result()
    result.boxes=_Boxes([1, 1], [.8], [[1, 2, 3, 4]])
    with pytest.raises(ValueError):
        detections_from_ultralytics(result)


class _Model:
    def __init__(self):
        self.kwargs=None
    def predict(self, **kwargs):
        self.kwargs=kwargs
        return [_Result()]


def test_inference_boundary_passes_explicit_threshold_and_disables_verbose_output():
    model=_Model()
    detections=infer_ultralytics(model, object(), confidence=.42)
    assert detections[0].class_name == "hotspot"
    assert model.kwargs["conf"] == .42
    assert model.kwargs["verbose"] is False


@pytest.mark.parametrize("confidence", [-.1, 1.1])
def test_inference_boundary_rejects_invalid_threshold(confidence):
    with pytest.raises(ValueError):
        infer_ultralytics(_Model(), object(), confidence=confidence)


def test_inference_boundary_requires_exactly_one_result():
    class EmptyModel:
        def predict(self, **kwargs):
            return []
    with pytest.raises(ValueError):
        infer_ultralytics(EmptyModel(), object())
