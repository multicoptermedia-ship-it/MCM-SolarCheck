"""Reproducible package metadata for model distribution decisions."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json

from .model_release import ModelRelease


@dataclass(frozen=True)
class ModelPackageManifest:
    release_id: str
    run_id: str
    weights_sha256: str
    model_format: str
    backend: str
    backend_version: str
    preprocessing: str
    distribution_rights_verified: bool

    def __post_init__(self) -> None:
        for name,value in (("release_id",self.release_id),("run_id",self.run_id),("model_format",self.model_format),("backend",self.backend),("backend_version",self.backend_version),("preprocessing",self.preprocessing)):
            if not isinstance(value,str) or not value.strip():
                raise ValueError(f"{name} must not be empty")
        if len(self.weights_sha256)!=64 or any(c not in "0123456789abcdefABCDEF" for c in self.weights_sha256):
            raise ValueError("weights_sha256 must be a SHA-256 digest")
        if not isinstance(self.distribution_rights_verified,bool):
            raise ValueError("distribution_rights_verified must be boolean")

    @property
    def package_id(self) -> str:
        payload={k:getattr(self,k) for k in self.__dataclass_fields__}
        return sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()

    @property
    def distributable(self) -> bool:
        return self.distribution_rights_verified


def build_model_package_manifest(release: ModelRelease, run, artifact, *, distribution_rights_verified: bool) -> ModelPackageManifest:
    if release.run_id!=run.run_id or artifact.run_id!=run.run_id:
        raise ValueError("package lineage does not match model release")
    if release.weights_sha256.lower()!=artifact.weights_sha256.lower():
        raise ValueError("package weights do not match model release")
    return ModelPackageManifest(release.release_id,run.run_id,artifact.weights_sha256.lower(),artifact.model_format,run.trainer,run.trainer_version,run.preprocessing,distribution_rights_verified)


def require_model_distribution(manifest: ModelPackageManifest) -> None:
    if not manifest.distribution_rights_verified:
        raise PermissionError("model weights cannot be distributed until rights are verified")
