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

    def __post_init__(self) -> None:
        for name,value in (
            ("provider",self.provider), ("model_version",self.model_version),
            ("dataset",self.dataset), ("license_id",self.license_id),
        ):
            if not value.strip():
                raise ValueError(f"{name} must not be empty")
        if self.modality not in {"thermal", "rgb"}:
            raise ValueError("model modality must be thermal or rgb")
        if self.weights_sha256 is not None:
            digest=self.weights_sha256.strip().casefold()
            if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                raise ValueError("weights_sha256 must be a 64-character hexadecimal SHA-256")
