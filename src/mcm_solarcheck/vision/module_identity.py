"""Stable physical PV-module identities across overlapping frames.

Per-frame detector labels are observations, not physical module IDs.  This module
keeps that distinction explicit and only reuses an identity when geometry gives a
sufficiently unambiguous match.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot
from typing import Iterable


Point = tuple[float, float]


@dataclass(frozen=True)
class ModuleObservation:
    frame_id: str
    local_id: str
    center: Point
    width: float
    height: float

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("module dimensions must be positive")


@dataclass
class PhysicalModule:
    module_id: str
    observations: list[ModuleObservation] = field(default_factory=list)

    @property
    def last(self) -> ModuleObservation:
        return self.observations[-1]


@dataclass(frozen=True)
class IdentityAssignment:
    observation: ModuleObservation
    module_id: str | None
    status: str
    normalized_distance: float | None


class ModuleIdentityTracker:
    """Conservative tracker for observations already expressed in one coordinate space.

    The caller must first transform observations into a common roof/RGB/world coordinate
    space.  This class deliberately does not infer cross-sensor geometry.
    """

    def __init__(self, *, max_normalized_distance: float = 0.35, ambiguity_margin: float = 0.10):
        if max_normalized_distance <= 0 or ambiguity_margin < 0:
            raise ValueError("invalid identity thresholds")
        self.max_normalized_distance = max_normalized_distance
        self.ambiguity_margin = ambiguity_margin
        self.modules: dict[str, PhysicalModule] = {}
        self.coordinate_space_id: str | None = None
        self._next_id = 1

    @staticmethod
    def _distance(a: ModuleObservation, b: ModuleObservation) -> float:
        scale = max((a.width + b.width) / 2.0, 1e-9)
        return hypot(a.center[0] - b.center[0], a.center[1] - b.center[1]) / scale

    def _new_module(self, obs: ModuleObservation) -> IdentityAssignment:
        module_id = f"M-{self._next_id:04d}"
        self._next_id += 1
        self.modules[module_id] = PhysicalModule(module_id, [obs])
        return IdentityAssignment(obs, module_id, "new", None)

    def assign(self, obs: ModuleObservation) -> IdentityAssignment:
        if not self.modules:
            return self._new_module(obs)

        ranked = sorted(
            ((self._distance(obs, module.last), module) for module in self.modules.values()),
            key=lambda item: item[0],
        )
        best_distance, best = ranked[0]
        if best_distance > self.max_normalized_distance:
            return self._new_module(obs)

        if len(ranked) > 1:
            second_distance = ranked[1][0]
            if second_distance - best_distance < self.ambiguity_margin:
                return IdentityAssignment(obs, None, "ambiguous", best_distance)

        # Never attach two detector observations from the same frame to one physical module.
        if best.last.frame_id == obs.frame_id:
            return self._new_module(obs)

        best.observations.append(obs)
        return IdentityAssignment(obs, best.module_id, "matched", best_distance)

    def assign_many(self, observations: Iterable[ModuleObservation]) -> list[IdentityAssignment]:
        return [self.assign(obs) for obs in observations]
