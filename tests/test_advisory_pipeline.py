import pytest

from mcm_solarcheck.domain.models import Finding
from mcm_solarcheck.review.advisory_pipeline import apply_yolo_advisory
from mcm_solarcheck.review.defect_classes import DEFAULT_THERMAL_CLASS_MAP
from mcm_solarcheck.review.inference_evidence import ModuleInferenceEvidence
from mcm_solarcheck.review.model_manifest import ModelManifest
from mcm_solarcheck.review.yolo_adapter import YoloAdapter, YoloDetection


def _parts():
    adapter=YoloAdapter("pv-yolo", "v1", DEFAULT_THERMAL_CLASS_MAP, "thermal")
    manifest=ModelManifest("pv-yolo", "v1", "thermal", "dataset-r1", "Apache-2.0", "a"*64)
    evidence=ModuleInferenceEvidence("M-42", "T-1", "thermal", (0, 0, 100, 200))
    finding=Finding("F-1", "T-1", 10, 20, module_id="M-42")
    return finding,adapter,manifest,evidence


def test_advisory_pipeline_attaches_best_defect_and_full_provenance():
    finding,adapter,manifest,evidence=_parts()
    result=apply_yolo_advisory(
        finding,
        detections=(YoloDetection("normal", .99), YoloDetection("hotspot", .84)),
        adapter=adapter, evidence=evidence, manifest=manifest,
    )
    assert result.reviewer_status == "unreviewed"
    assert result.metadata["classification_status"] == "suggested"
    assert result.metadata["classification_label"] == "thermal_hotspot_candidate"
    assert result.metadata["classification_dataset"] == "dataset-r1"
    assert result.metadata["classification_weights_sha256"] == "a"*64


def test_advisory_pipeline_leaves_finding_unchanged_without_defect():
    finding,adapter,manifest,evidence=_parts()
    result=apply_yolo_advisory(
        finding, detections=(YoloDetection("normal", .99),),
        adapter=adapter, evidence=evidence, manifest=manifest,
    )
    assert result is finding
    assert "classification_status" not in result.metadata


def test_advisory_pipeline_rejects_manifest_adapter_mismatch():
    finding,adapter,_,evidence=_parts()
    manifest=ModelManifest("other", "v1", "thermal", "dataset", "license")
    with pytest.raises(ValueError):
        apply_yolo_advisory(
            finding, detections=(YoloDetection("hotspot", .8),),
            adapter=adapter, evidence=evidence, manifest=manifest,
        )
