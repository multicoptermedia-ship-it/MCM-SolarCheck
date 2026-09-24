"""Optional Ultralytics training adapter behind the controlled trainer boundary."""
from __future__ import annotations
from pathlib import Path

from .trainer_config import YoloTrainerConfig


def ultralytics_trainer(config: YoloTrainerConfig, *, model, output_dir):
    """Return a trainer callable compatible with execute_training.

    The model object is injected so the core package does not import or require
    Ultralytics. Exact backend/version and parameters remain in TrainingRun.
    """
    if config.backend.casefold()!="ultralytics":
        raise ValueError("Ultralytics adapter requires backend='ultralytics'")
    if not hasattr(model,"train") or not callable(model.train):
        raise ValueError("Ultralytics model must provide callable train()")
    root=Path(output_dir)

    def train(dataset_build, run):
        expected=config.training_run(dataset_build,preprocessing=run.preprocessing)
        if expected.run_id!=run.run_id:
            raise ValueError("trainer configuration does not match TrainingRun lineage")
        result=model.train(
            data=str(dataset_build.path) if hasattr(dataset_build,"path") else str(dataset_build.dataset_id),
            epochs=config.epochs,
            imgsz=config.image_size,
            batch=config.batch_size,
            seed=config.seed,
            device=config.device,
            project=str(root),
        )
        candidates=[]
        save_dir=getattr(result,"save_dir",None)
        if save_dir:
            candidates.append(Path(save_dir)/"weights"/"best.pt")
        candidates.append(root/"weights"/"best.pt")
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        raise ValueError("Ultralytics training did not produce best.pt")

    return train
