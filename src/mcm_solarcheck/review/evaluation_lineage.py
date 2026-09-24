"""Independent evaluation-set lineage for trained model release decisions."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json

from .model_lineage import TrainingRun
from .model_validation import ModelValidationSummary


@dataclass(frozen=True)
class EvaluationSet:
    dataset_id: str
    snapshot_id: str
    representative_m3t: bool

    def __post_init__(self) -> None:
        for name,value in (("dataset_id",self.dataset_id),("snapshot_id",self.snapshot_id)):
            if not isinstance(value,str) or not value.strip():
                raise ValueError(f"{name} must not be empty")
        if not isinstance(self.representative_m3t,bool):
            raise ValueError("representative_m3t must be boolean")

    @property
    def evaluation_id(self) -> str:
        payload={"dataset_id":self.dataset_id,"snapshot_id":self.snapshot_id,"representative_m3t":self.representative_m3t}
        return sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()


@dataclass(frozen=True)
class IndependentModelEvaluation:
    evaluation_set: EvaluationSet
    summary: ModelValidationSummary

    def __post_init__(self) -> None:
        if self.summary.representative_m3t != self.evaluation_set.representative_m3t:
            raise ValueError("validation summary does not match evaluation-set provenance")


def require_independent_evaluation(training_run: TrainingRun, evaluation: IndependentModelEvaluation) -> None:
    if evaluation.evaluation_set.dataset_id == training_run.dataset_id:
        raise ValueError("evaluation dataset must be independent from training dataset")
    if evaluation.evaluation_set.snapshot_id == training_run.snapshot_id:
        raise ValueError("evaluation snapshot must be independent from training snapshot")
