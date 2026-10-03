import pytest

from mcm_solarcheck.domain.models import Finding
from mcm_solarcheck.review.defect_classes import DEFAULT_THERMAL_CLASS_MAP
from mcm_solarcheck.review.inference_evidence import (
    ModuleInferenceEvidence,
    attach_yolo_module_suggestion,
    attach_manifest_provenance,
)
from mcm_solarcheck.review.yolo_adapter import YoloAdapter, YoloDetection
from mcm_solarcheck.review.model_manifest import ModelManifest


def _adapter(modality="thermal"):
    return YoloAdapter("fixture-yolo", "v1", DEFAULT_THERMAL_CLASS_MAP, modality)


def _finding(module_id="M-0042", frame_id="T-1"):
    return Finding("F-1", frame_id, 10, 20, module_id=module_id)


def _evidence(module_id="M-0042", frame_id="T-1", modality="thermal", paired_thermal_frame_id=None):
    return ModuleInferenceEvidence(
        module_id, frame_id, modality, (1, 2, 101, 202), paired_thermal_frame_id
    )


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


def test_manifest_provenance_is_attached_after_model_suggestion():
    classified=attach_yolo_module_suggestion(
        _finding(), detection=YoloDetection("hotspot", .91),
        adapter=_adapter(), evidence=_evidence(),
    )
    manifest=ModelManifest("fixture-yolo", "v1", "thermal", "pv-dataset-r1", "CC-BY-4.0", "a"*64)
    result=attach_manifest_provenance(classified, manifest)
    assert result.metadata["classification_dataset"] == "pv-dataset-r1"
    assert result.metadata["classification_license"] == "CC-BY-4.0"
    assert result.metadata["classification_weights_sha256"] == "a"*64


@pytest.mark.parametrize("manifest", [
    ModelManifest("other", "v1", "thermal", "dataset", "license"),
    ModelManifest("fixture-yolo", "v2", "thermal", "dataset", "license"),
    ModelManifest("fixture-yolo", "v1", "rgb", "dataset", "license"),
])
def test_mismatched_manifest_cannot_claim_model_provenance(manifest):
    classified=attach_yolo_module_suggestion(
        _finding(), detection=YoloDetection("hotspot", .91),
        adapter=_adapter(), evidence=_evidence(),
    )
    with pytest.raises(ValueError):
        attach_manifest_provenance(classified, manifest)


def test_rgb_evidence_resolves_through_explicit_image_pair_identity():
    result=attach_yolo_module_suggestion(
        _finding(frame_id="T-1"),
        detection=YoloDetection("hotspot", .8),
        adapter=_adapter("rgb"),
        evidence=_evidence("M-0042", "RGB-7", "rgb", "T-1"),
    )
    assert result.metadata["classification_source_frame_id"] == "RGB-7"
    assert result.metadata["classification_paired_thermal_frame_id"] == "T-1"
    assert result.metadata["classification_modality"] == "rgb"


def test_rgb_evidence_without_pair_identity_fails_closed():
    with pytest.raises(ValueError):
        _evidence("M-0042", "RGB-7", "rgb")


def test_rgb_evidence_cannot_attach_to_different_thermal_pair():
    with pytest.raises(ValueError):
        attach_yolo_module_suggestion(
            _finding(frame_id="T-1"),
            detection=YoloDetection("hotspot", .8),
            adapter=_adapter("rgb"),
            evidence=_evidence("M-0042", "RGB-7", "rgb", "T-9"),
        )


def test_manifest_runtime_provenance_is_persisted():
    classified=attach_yolo_module_suggestion(
        _finding(), detection=YoloDetection("hotspot", .91),
        adapter=_adapter(), evidence=_evidence(),
    )
    manifest=ModelManifest(
        "fixture-yolo", "v1", "thermal", "pv-dataset-r1", "Apache-2.0",
        preprocessing="thermal-render-v1", backend="ultralytics-8.x",
    )
    result=attach_manifest_provenance(classified, manifest)
    assert result.metadata["classification_preprocessing"] == "thermal-render-v1"
    assert result.metadata["classification_backend"] == "ultralytics-8.x"
