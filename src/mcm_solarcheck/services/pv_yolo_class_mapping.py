"""Explicit, reviewable mappings from external YOLO classes to PV observations."""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.pv_ai_fault_taxonomy import ObservationKind
from mcm_solarcheck.services.pv_dataset_intake import ImageModality


@dataclass(frozen=True)
class YoloClassMapping:
    external_names: tuple[str, ...]
    mapped_observations: tuple[ObservationKind | None, ...]
    modality: ImageModality

    def __post_init__(self) -> None:
        if not isinstance(self.modality, ImageModality) or self.modality is ImageModality.EL:
            raise ValueError("only RGB and thermal class mappings supported in v1")
        if not self.external_names or len(self.external_names) != len(self.mapped_observations):
            raise ValueError("complete ordered class vocabulary required")
        if any(not name.strip() for name in self.external_names):
            raise ValueError("blank external class")
        if len(set(self.external_names)) != len(self.external_names):
            raise ValueError("duplicate external classes")
        for observation in self.mapped_observations:
            if observation is None:
                continue
            if not isinstance(observation, ObservationKind):
                raise ValueError("mapping must target an observable signature")
            prefix = "rgb_" if self.modality is ImageModality.RGB else "thermal_"
            if not observation.value.startswith(prefix):
                raise ValueError("mapping modality mismatch")

    def observation_for_class(self, class_id: int) -> ObservationKind | None:
        if type(class_id) is not int or not 0 <= class_id < len(self.external_names):
            raise ValueError("unknown YOLO class ID")
        return self.mapped_observations[class_id]
