"""End-to-end advisory inference orchestration for Phase 7."""
from __future__ import annotations

from mcm_solarcheck.domain.models import Finding

from .inference_evidence import (
    ModuleInferenceEvidence,
    attach_manifest_provenance,
    attach_yolo_module_suggestion,
)
from .model_manifest import ModelManifest
from .yolo_adapter import YoloAdapter, YoloDetection


def apply_yolo_advisory(
    finding: Finding,
    *,
    detections: tuple[YoloDetection, ...],
    adapter: YoloAdapter,
    evidence: ModuleInferenceEvidence,
    manifest: ModelManifest,
) -> Finding:
    """Attach the best defect suggestion and complete provenance, if one exists."""
    if manifest.provider.strip() != adapter.provider.strip():
        raise ValueError("manifest and adapter provider must match")
    if manifest.model_version.strip() != adapter.model_version.strip():
        raise ValueError("manifest and adapter model version must match")
    if manifest.modality != adapter.modality:
        raise ValueError("manifest and adapter modality must match")

    best=adapter.select_best(detections)
    if best is None:
        return finding

    classified=attach_yolo_module_suggestion(
        finding, detection=best, adapter=adapter, evidence=evidence
    )
    return attach_manifest_provenance(classified, manifest)
