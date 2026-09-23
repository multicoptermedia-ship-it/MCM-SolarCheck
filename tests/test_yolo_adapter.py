import pytest

from mcm_solarcheck.review.defect_classes import DEFAULT_THERMAL_CLASS_MAP
from mcm_solarcheck.review.yolo_adapter import YoloAdapter, YoloDetection


def _adapter():
    return YoloAdapter("yolo-pv-thermal", "v1", DEFAULT_THERMAL_CLASS_MAP, "thermal")


def test_yolo_detection_maps_to_advisory_classification():
    result=_adapter().adapt(YoloDetection("Hot Spot", .87, (1,2,20,30)))
    assert result.label == "thermal_hotspot_candidate"
    assert result.confidence == .87
    assert result.provider == "yolo-pv-thermal"
    assert result.model_version == "v1"
    assert result.modality == "thermal"


def test_best_detection_ignores_unknown_external_class():
    result=_adapter().adapt_best((
        YoloDetection("mystery", .99),
        YoloDetection("cell hotspot", .81),
    ))
    assert result is not None
    assert result.label == "cell_hotspot_candidate"


def test_best_detection_is_deterministic_on_equal_confidence():
    result=_adapter().adapt_best((
        YoloDetection("short circuit", .8),
        YoloDetection("open circuit", .8),
    ))
    assert result is not None
    assert result.label == "open_circuit_candidate"


def test_only_unknown_detections_produce_no_best_suggestion():
    assert _adapter().adapt_best((YoloDetection("mystery", .99),)) is None


@pytest.mark.parametrize("confidence", [float("nan"), float("inf"), -.1, 1.1])
def test_yolo_detection_rejects_invalid_confidence(confidence):
    with pytest.raises(ValueError):
        YoloDetection("hotspot", confidence)


@pytest.mark.parametrize("box", [
    (0,0,0,1), (0,0,1,0), (2,0,1,1),
    (0,0,float("nan"),1), (0,0,float("inf"),1),
])
def test_yolo_detection_rejects_invalid_boxes(box):
    with pytest.raises(ValueError):
        YoloDetection("hotspot", .5, box)


@pytest.mark.parametrize("modality", ["", "mixed", "infrared"])
def test_yolo_adapter_requires_explicit_supported_modality(modality):
    with pytest.raises(ValueError):
        YoloAdapter("model", "v1", DEFAULT_THERMAL_CLASS_MAP, modality)
