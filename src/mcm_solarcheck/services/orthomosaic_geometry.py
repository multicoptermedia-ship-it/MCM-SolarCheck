"""Geometry readiness for module-plane orthomosaic processing, not reconstruction."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from mcm_solarcheck.domain.models import Pose


@dataclass(frozen=True)
class ModulePlane:
    plane_id: str
    tilt_deg: float
    azimuth_deg: float
    provenance: str

    def __post_init__(self) -> None:
        if not self.plane_id.strip() or not self.provenance.strip():
            raise ValueError("plane identifier and provenance required")
        if not all(isfinite(v) for v in (self.tilt_deg, self.azimuth_deg)):
            raise ValueError("nonfinite plane geometry")
        if not 0 <= self.tilt_deg <= 90 or not 0 <= self.azimuth_deg < 360:
            raise ValueError("invalid plane tilt or azimuth")


@dataclass(frozen=True)
class CameraOrientation:
    yaw_deg: float
    pitch_deg: float
    roll_deg: float

    @classmethod
    def from_dji_pose(cls, pose: Pose) -> "CameraOrientation":
        values = (pose.yaw_deg, pose.pitch_deg, pose.roll_deg)
        if any(v is None or not isfinite(v) for v in values):
            raise ValueError("complete finite DJI gimbal pose required")
        yaw, pitch, roll = values
        if not -180 <= pitch <= 180 or not -180 <= roll <= 180:
            raise ValueError("invalid gimbal pitch or roll")
        return cls(yaw, pitch, roll)


@dataclass(frozen=True)
class GeometryReadiness:
    plane: ModulePlane
    cameras: tuple[CameraOrientation, ...]
    ready_for_reconstruction_attempt: bool
    notes: tuple[str, ...]


def assess_geometry_readiness(plane: ModulePlane, poses: tuple[Pose, ...]) -> GeometryReadiness:
    """Validate metadata presence, never assert incidence angle or ortho success."""
    if not poses:
        return GeometryReadiness(plane, (), False, ("no camera poses supplied",))
    cameras = []
    for index, pose in enumerate(poses):
        try:
            cameras.append(CameraOrientation.from_dji_pose(pose))
        except ValueError:
            return GeometryReadiness(plane, tuple(cameras), False,
                                     (f"missing or invalid gimbal pose at index {index}",))
    return GeometryReadiness(plane, tuple(cameras), True,
                             ("camera metadata available; calibration, overlap and registration unverified",))
