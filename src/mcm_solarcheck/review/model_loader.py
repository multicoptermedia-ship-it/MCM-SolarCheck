"""Controlled loading of external Ultralytics model artifacts."""
from __future__ import annotations

from .model_manifest import ModelManifest, verify_weights_sha256


def load_verified_ultralytics_model(
    manifest: ModelManifest,
    weights_path: object,
    *,
    yolo_factory: object,
) -> object:
    """Load weights only after immutable artifact verification succeeds."""
    if not verify_weights_sha256(manifest, weights_path):
        raise ValueError("model weights SHA-256 does not match manifest")
    if not callable(yolo_factory):
        raise ValueError("YOLO factory must be callable")
    return yolo_factory(str(weights_path))
