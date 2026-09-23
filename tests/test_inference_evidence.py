import pytest

from mcm_solarcheck.domain.models import Finding
from mcm_solarcheck.review.defect_classes import DEFAULT_THERMAL_CLASS_MAP
from mcm_solarcheck.review.inference_evidence import (
    ModuleInferenceEvidence,
    attach_yolo_module_suggestion,
)
from mcm_solarcheck.review.yolo_adapter import YoloAdapter, YoloDetection


def _adapter(modality="thermal"):
    return YoloAdapter("fixture-yolo", "v1", DEFAULT_THERMAL_CLASS_MAP, modality)


def _finding(module_id="M-0042", frame_id="T-1"):
    return Finding("F-1", frame_id, 10, 20, module_id=module_id)


def _evidence(module_id="M-0042", frame_id="T-1", modality="thermal"):
    return ModuleInferenceEvidence(module_id, frame_id, modality, (1, 2, 101, 202))


def test_yolo_suggestion_retains_module_crop_provenance():
    result=attach_yolo_module_suggestion(
        _finding(), detection=YoloDetection("hotspot", .91),
        adapter=_adapter(), evidence=_evidence(),
    )
    assert result.module_id == "M-0042"
    assert result.metadata["classification_module_id"] == "M-0042"
    assert result.metadata["classification_source_frame_id"] == "T-1"
    assert result.metadata["classification_modality"] == "thermal"
    assert result.metadata["classification_crop_xyxy"] == "1.0,2.0,101.0,202.0"


@pytest.mark.parametrize("finding,evidence", [
    (_finding("M-0042"), _evidence("M-0099")),
    (_finding(frame_id="T-1"), _evidence(frame_id="T-2")),
])
def test_mismatched_identity_fails_closed(finding, evidence):
    with pytest.raises(ValueError):
        attach_yolo_module_suggestion(
            finding, detection=YoloDetection("hotspot", .8),
            adapter=_adapter(), evidence=evidence,
        )


def test_mismatched_modality_fails_closed():
    with pytest.raises(ValueError):
        attach_yolo_module_suggestion(
            _finding(), detection=YoloDetection("hotspot", .8),
            adapter=_adapter("rgb"), evidence=_evidence("M-0042", "T-1", "thermal"),
        )


def test_unlocalized_finding_cannot_receive_module_model_evidence():
    with pytest.raises(ValueError):
        attach_yolo_module_suggestion(
            _finding(None), detection=YoloDetection("hotspot", .8),
            adapter=_adapter(), evidence=_evidence(),
        )


@pytest.mark.parametrize("crop", [
    (0,0,0,1), (0,0,1,0), (0,0,float("nan"),1), (0,0,float("inf"),1),
])
def test_invalid_module_crop_fails_closed(crop):
    with pytest.raises(ValueError):
        ModuleInferenceEvidence("M-1", "T-1", "thermal", crop)
