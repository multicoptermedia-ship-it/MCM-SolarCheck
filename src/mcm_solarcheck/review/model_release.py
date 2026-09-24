"""Immutable release record for a validated MCM-owned model."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json

from .trained_model_validation import TrainedModelValidation, require_trained_model_validation


@dataclass(frozen=True)
class ModelRelease:
    release_id: str
    run_id: str
    weights_sha256: str
    evaluator: str


def create_model_release(validation: TrainedModelValidation) -> ModelRelease:
    require_trained_model_validation(validation)
    artifact=validation.artifact
    payload={"run_id":artifact.run_id,"weights_sha256":artifact.weights_sha256.lower(),"evaluator":validation.evaluator.strip()}
    encoded=json.dumps(payload,sort_keys=True,separators=(",",":"))
    return ModelRelease(sha256(encoded.encode()).hexdigest(),artifact.run_id,artifact.weights_sha256.lower(),validation.evaluator.strip())
