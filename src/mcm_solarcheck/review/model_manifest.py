"""Auditable provenance for pretrained Phase 7 models."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelManifest:
    provider: str
    model_version: str
    modality: str
    dataset: str
    license_id: str
    weights_sha256: str | None = None
    preprocessing: str | None = None
    backend: str | None = None

    def __post_init__(self) -> None:
        for name,value in (
            ("provider",self.provider), ("model_version",self.model_version),
            ("dataset",self.dataset), ("license_id",self.license_id),
        ):
            if not value.strip():
                raise ValueError(f"{name} must not be empty")
        if self.modality not in {"thermal", "rgb"}:
            raise ValueError("model modality must be thermal or rgb")
        for name,value in (("preprocessing",self.preprocessing),("backend",self.backend)):
            if value is not None and not value.strip():
                raise ValueError(f"{name} must not be blank")
        if self.weights_sha256 is not None:
            digest=self.weights_sha256.strip().casefold()
            if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                raise ValueError("weights_sha256 must be a 64-character hexadecimal SHA-256")


def verify_weights_sha256(manifest: ModelManifest, path: object) -> bool:
    """Verify an external weight artifact against its recorded immutable digest."""
    from hashlib import sha256
    from pathlib import Path

    if manifest.weights_sha256 is None:
        raise ValueError("model manifest has no weights SHA-256")
    weight_path=Path(path)
    if not weight_path.is_file():
        raise ValueError("model weights file does not exist")

    digest=sha256()
    with weight_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest() == manifest.weights_sha256.strip().casefold()
