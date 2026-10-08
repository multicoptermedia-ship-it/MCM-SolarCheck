"""Geometry contracts for RGB/thermal evidence alignment.

Pairing proves that two captures belong together. It does not prove that their
pixel coordinate systems are interchangeable. This module makes that boundary
explicit and provides a conservative gate for future image registration.
"""
from __future__ import annotations
from dataclasses import dataclass
from mcm_solarcheck.domain.models import ImageFrame

@dataclass(frozen=True)
class CaptureGeometryDelta:
    time_delta_s: float | None
    gimbal_yaw_delta_deg: float | None
    gimbal_pitch_delta_deg: float | None
    flight_yaw_delta_deg: float | None

@dataclass(frozen=True)
class PixelTransform:
    method: str
    validated: bool
    source_width: int
    source_height: int
    target_width: int
    target_height: int
    matrix: tuple[tuple[float,float,float],tuple[float,float,float],tuple[float,float,float]] | None = None
    validation_error_px: float | None = None

    def map_point(self,x:float,y:float)->tuple[float,float]:
        if not self.validated or self.matrix is None:
            raise RuntimeError('RGB/thermal pixel transform has not been validated')
        m=self.matrix
        den=m[2][0]*x+m[2][1]*y+m[2][2]
        if den==0: raise ValueError('Transform maps point to infinity')
        return ((m[0][0]*x+m[0][1]*y+m[0][2])/den,(m[1][0]*x+m[1][1]*y+m[1][2])/den)

def capture_geometry_delta(rgb:ImageFrame,thermal:ImageFrame)->CaptureGeometryDelta:
    def diff(a,b): return None if a is None or b is None else abs(a-b)
    dt=None
    if rgb.timestamp_utc is not None and thermal.timestamp_utc is not None:
        dt=abs((rgb.timestamp_utc-thermal.timestamp_utc).total_seconds())
    return CaptureGeometryDelta(dt,diff(rgb.camera_pose.yaw_deg,thermal.camera_pose.yaw_deg),diff(rgb.camera_pose.pitch_deg,thermal.camera_pose.pitch_deg),diff(rgb.flight_pose.yaw_deg,thermal.flight_pose.yaw_deg))

def unavailable_transform(*,thermal_width:int=640,thermal_height:int=512,rgb_width:int=4000,rgb_height:int=3000)->PixelTransform:
    return PixelTransform('unvalidated',False,thermal_width,thermal_height,rgb_width,rgb_height)
