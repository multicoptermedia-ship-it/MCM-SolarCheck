"""Explicit reproducible trainer configuration for Phase 8 model training."""
from __future__ import annotations
from dataclasses import dataclass

from .model_lineage import TrainingRun


@dataclass(frozen=True)
class YoloTrainerConfig:
    backend: str
    backend_version: str
    epochs: int
    image_size: int
    batch_size: int
    seed: int
    device: str = "auto"

    def __post_init__(self) -> None:
        for name,value in (("backend",self.backend),("backend_version",self.backend_version),("device",self.device)):
            if not isinstance(value,str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        for name,value in (("epochs",self.epochs),("image_size",self.image_size),("batch_size",self.batch_size)):
            if not isinstance(value,int) or isinstance(value,bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if not isinstance(self.seed,int) or isinstance(self.seed,bool) or self.seed < 0:
            raise ValueError("seed must be a non-negative integer")

    def training_run(self, dataset_build, *, preprocessing: str) -> TrainingRun:
        return TrainingRun(
            dataset_id=dataset_build.dataset_id,
            snapshot_id=dataset_build.snapshot_id,
            trainer=self.backend,
            trainer_version=self.backend_version,
            preprocessing=preprocessing,
            parameters={
                "epochs":self.epochs,
                "imgsz":self.image_size,
                "batch":self.batch_size,
                "seed":self.seed,
                "device":self.device,
            },
        )
