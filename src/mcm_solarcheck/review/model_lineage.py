"""Lineage contract for models trained from MCM dataset builds."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json


@dataclass(frozen=True)
class TrainingRun:
    dataset_id: str
    snapshot_id: str
    trainer: str
    trainer_version: str
    preprocessing: str
    parameters: dict[str, object]

    def __post_init__(self) -> None:
        for name,value in (("dataset_id",self.dataset_id),("snapshot_id",self.snapshot_id),("trainer",self.trainer),("trainer_version",self.trainer_version),("preprocessing",self.preprocessing)):
            if not isinstance(value,str) or not value.strip():
                raise ValueError(f"{name} must not be empty")

    @property
    def run_id(self) -> str:
        payload={"dataset_id":self.dataset_id,"snapshot_id":self.snapshot_id,"trainer":self.trainer,"trainer_version":self.trainer_version,"preprocessing":self.preprocessing,"parameters":self.parameters}
        encoded=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        return sha256(encoded.encode()).hexdigest()


@dataclass(frozen=True)
class TrainedModelArtifact:
    run_id: str
    weights_sha256: str
    model_format: str

    def __post_init__(self) -> None:
        if len(self.weights_sha256)!=64 or any(c not in "0123456789abcdefABCDEF" for c in self.weights_sha256):
            raise ValueError("model weights SHA-256 must be 64 hexadecimal characters")
        if not self.run_id.strip() or not self.model_format.strip():
            raise ValueError("model artifact lineage fields must not be empty")
