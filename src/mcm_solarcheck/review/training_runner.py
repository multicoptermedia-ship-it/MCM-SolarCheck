"""Controlled training execution boundary.

The caller supplies the trainer implementation. This module records exactly what
was trained and verifies the resulting weight bytes; it does not auto-deploy.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path

from .model_lineage import TrainingRun, TrainedModelArtifact


def execute_training(dataset_build, run: TrainingRun, *, trainer) -> TrainedModelArtifact:
    if run.dataset_id != dataset_build.dataset_id or run.snapshot_id != dataset_build.snapshot_id:
        raise ValueError("training run does not match dataset build lineage")
    if not callable(trainer):
        raise ValueError("trainer must be callable")
    weights_path=Path(trainer(dataset_build,run))
    if not weights_path.is_file():
        raise ValueError("trainer did not produce a weights file")
    digest=sha256(weights_path.read_bytes()).hexdigest()
    return TrainedModelArtifact(run.run_id,digest,weights_path.suffix.lstrip(".") or "unknown")
