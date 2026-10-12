"""Explicit inputs for later orthomosaic workers; no fabricated rasters."""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.domain.models import Pose
from mcm_solarcheck.services.orthomosaic_geometry import (
    GeometryReadiness, ModulePlane, assess_geometry_readiness,
)


@dataclass(frozen=True)
class ReconstructionPlan:
    project_id: str
    view: str
    readiness: GeometryReadiness
    rgb_frame_ids: tuple[str, ...]
    thermal_frame_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.project_id.strip():
            raise ValueError("project id required")
        if self.view not in ("horizontal_overview", "module_plane"):
            raise ValueError("unknown orthomosaic view")
        if len(self.rgb_frame_ids) != len(self.thermal_frame_ids) or not self.rgb_frame_ids:
            raise ValueError("paired RGB and thermal frames required")
        if len(set(self.rgb_frame_ids)) != len(self.rgb_frame_ids):
            raise ValueError("duplicate RGB frame ids")
        if len(set(self.thermal_frame_ids)) != len(self.thermal_frame_ids):
            raise ValueError("duplicate thermal frame ids")
        if len(self.readiness.cameras) != len(self.rgb_frame_ids) or not self.readiness.ready_for_reconstruction_attempt:
            raise ValueError("all camera orientations must be available")


def plan_module_plane_reconstruction(
    project_id: str, plane: ModulePlane,
    rgb_frame_ids: tuple[str, ...], thermal_frame_ids: tuple[str, ...],
    gimbal_poses: tuple[Pose, ...],
) -> ReconstructionPlan:
    readiness = assess_geometry_readiness(plane, gimbal_poses)
    return ReconstructionPlan(project_id, "module_plane", readiness, rgb_frame_ids, thermal_frame_ids)
