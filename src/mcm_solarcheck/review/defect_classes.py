"""Canonical Phase 7 defect vocabulary and external dataset mapping.

External labels are normalized before they enter MCM-SolarCheck. Unknown labels
remain explicit instead of being guessed into a diagnostic category.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DefectClass(str, Enum):
    THERMAL_HOTSPOT_CANDIDATE = "thermal_hotspot_candidate"
    CELL_HOTSPOT_CANDIDATE = "cell_hotspot_candidate"
    MULTI_CELL_HOTSPOT_CANDIDATE = "multi_cell_hotspot_candidate"
    SUBSTRING_ANOMALY_CANDIDATE = "substring_anomaly_candidate"
    OPEN_CIRCUIT_CANDIDATE = "open_circuit_candidate"
    SHORT_CIRCUIT_CANDIDATE = "short_circuit_candidate"
    SOILING_CANDIDATE = "soiling_candidate"
    NORMAL = "normal"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DatasetClassMap:
    dataset: str
    mapping: dict[str, DefectClass]

    def __post_init__(self) -> None:
        if not self.dataset.strip():
            raise ValueError("dataset must not be empty")

    def normalize(self, external_label: str) -> DefectClass:
        key=external_label.strip().casefold()
        if not key:
            return DefectClass.UNKNOWN
        normalized={label.strip().casefold(): target for label,target in self.mapping.items()}
        return normalized.get(key, DefectClass.UNKNOWN)


DEFAULT_THERMAL_CLASS_MAP = DatasetClassMap(
    "generic-pv-thermal",
    {
        "hotspot": DefectClass.THERMAL_HOTSPOT_CANDIDATE,
        "hot spot": DefectClass.THERMAL_HOTSPOT_CANDIDATE,
        "cell": DefectClass.CELL_HOTSPOT_CANDIDATE,
        "cell hotspot": DefectClass.CELL_HOTSPOT_CANDIDATE,
        "multi-cell": DefectClass.MULTI_CELL_HOTSPOT_CANDIDATE,
        "multi cell": DefectClass.MULTI_CELL_HOTSPOT_CANDIDATE,
        "substring": DefectClass.SUBSTRING_ANOMALY_CANDIDATE,
        "open-circuit": DefectClass.OPEN_CIRCUIT_CANDIDATE,
        "open circuit": DefectClass.OPEN_CIRCUIT_CANDIDATE,
        "short-circuit": DefectClass.SHORT_CIRCUIT_CANDIDATE,
        "short circuit": DefectClass.SHORT_CIRCUIT_CANDIDATE,
        "normal": DefectClass.NORMAL,
    },
)
