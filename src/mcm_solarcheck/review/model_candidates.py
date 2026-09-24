"""Known external model candidates for controlled Phase 7 validation."""
from __future__ import annotations

from .model_manifest import ModelManifest

PV_HSD_2025_YOLOV8S_P1 = ModelManifest(
    provider="PV-HSD-2025/yolov8s-p1",
    model_version="upstream-main",
    modality="thermal",
    dataset="PV-HSD-2025",
    license_id="research-only; commercial permission required",
    weights_sha256="f466bcc39afeed1389df40a487398bd6ca9137dbf649642f9a557ef63ec98bca",
    preprocessing="rendered_rgb",
    backend="Ultralytics YOLOv8-P1",
)

PV_HSD_2025_COMMERCIAL_USE_APPROVED = False
