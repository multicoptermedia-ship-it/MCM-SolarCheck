"""Module-scoped inference evidence for Phase 7 model adapters."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from mcm_solarcheck.domain.models import Finding

from .classification import attach_classification_suggestion
from .model_manifest import ModelManifest
from .yolo_adapter import YoloAdapter, YoloDetection


@dataclass(frozen=True)
class ModuleInferenceEvidence:
    module_id: str
    source_frame_id: str
    modality: str
    crop_xyxy: tuple[float, float, float, float]

    def __post_init__(self) -> None:
        if not self.module_id.strip() or not self.source_frame_id.strip():
            raise ValueError("module and source frame identity are required")
        if self.modality not in {"thermal", "rgb"}:
            raise ValueError("evidence modality must be thermal or rgb")
        x1,y1,x2,y2=self.crop_xyxy
        if not all(isfinite(float(v)) for v in self.crop_xyxy) or x2 <= x1 or y2 <= y1:
            raise ValueError("module crop must be finite with positive area")


def attach_yolo_module_suggestion(
    finding: Finding,
    *,
    detection: YoloDetection,
    adapter: YoloAdapter,
    evidence: ModuleInferenceEvidence,
) -> Finding:
    """Attach a YOLO suggestion only when its module evidence matches the finding."""
    if not finding.module_id or finding.module_id != evidence.module_id:
        raise ValueError("YOLO evidence must match the finding module")
    if finding.thermal_frame_id != evidence.source_frame_id:
        raise ValueError("YOLO evidence must match the finding source frame")
    if adapter.modality != evidence.modality:
        raise ValueError("YOLO adapter and evidence modality must match")

    classified=attach_classification_suggestion(finding, adapter.adapt(detection))
    metadata=dict(classified.metadata)
    metadata.update({
        "classification_module_id": evidence.module_id,
        "classification_source_frame_id": evidence.source_frame_id,
        "classification_crop_xyxy": ",".join(str(float(v)) for v in evidence.crop_xyxy),
    })
    from dataclasses import replace
    return replace(classified, metadata=metadata)


def attach_manifest_provenance(finding: Finding, manifest: ModelManifest) -> Finding:
    """Persist model/dataset provenance alongside an advisory suggestion."""
    from dataclasses import replace

    if finding.metadata.get("classification_provider") != manifest.provider.strip():
        raise ValueError("model manifest provider must match classification provider")
    if finding.metadata.get("classification_model_version") != manifest.model_version.strip():
        raise ValueError("model manifest version must match classification model version")
    if finding.metadata.get("classification_modality") != manifest.modality:
        raise ValueError("model manifest modality must match classification modality")

    metadata=dict(finding.metadata)
    metadata.update({
        "classification_dataset": manifest.dataset.strip(),
        "classification_license": manifest.license_id.strip(),
    })
    if manifest.weights_sha256:
        metadata["classification_weights_sha256"]=manifest.weights_sha256.strip().casefold()
    return replace(finding, metadata=metadata)
