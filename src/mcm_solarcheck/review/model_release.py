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


def attach_release_provenance(finding, release: ModelRelease, *, dataset_id: str, snapshot_id: str):
    """Bind advisory evidence to the exact validated release lineage."""
    from dataclasses import replace
    if not dataset_id.strip() or not snapshot_id.strip():
        raise ValueError("release dataset and snapshot ids must not be empty")
    metadata=dict(finding.metadata)
    metadata.update({
        "classification_release_id":release.release_id,
        "classification_training_run_id":release.run_id,
        "classification_weights_sha256":release.weights_sha256,
        "classification_dataset_id":dataset_id,
        "classification_snapshot_id":snapshot_id,
    })
    return replace(finding,metadata=metadata)
