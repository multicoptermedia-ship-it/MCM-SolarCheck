"""Domain models for imported RGB/Thermal frames.

These models deliberately contain no DJI SDK dependency. Vendor-specific readers
map their output into these neutral structures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Position:
    latitude: float
    longitude: float
    altitude_m: Optional[float] = None


@dataclass(frozen=True)
class Pose:
    yaw_deg: Optional[float] = None
    pitch_deg: Optional[float] = None
    roll_deg: Optional[float] = None


@dataclass(frozen=True)
class RTKQuality:
    status: Optional[str] = None
    std_lat_m: Optional[float] = None
    std_lon_m: Optional[float] = None
    std_height_m: Optional[float] = None
    correction_age_s: Optional[float] = None
    altitude_type: Optional[str] = None


@dataclass
class ImageFrame:
    frame_id: str
    source_file: Path
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    timestamp_utc: Optional[datetime] = None
    position: Optional[Position] = None
    camera_pose: Pose = field(default_factory=Pose)
    flight_pose: Pose = field(default_factory=Pose)
    rtk: RTKQuality = field(default_factory=RTKQuality)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class ThermalFrame(ImageFrame):
    thermal_width: Optional[int] = None
    thermal_height: Optional[int] = None
    temperature_unit: Optional[str] = None
    min_temperature_c: Optional[float] = None
    max_temperature_c: Optional[float] = None
    mean_temperature_c: Optional[float] = None
    thermal_source: str = "unknown"
    temperature_matrix: object | None = None
    calibration: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ImagePair:
    pair_id: str
    rgb_frame_id: str
    thermal_frame_id: str
    confidence: float
    method: str
    distance_m: Optional[float] = None
    time_delta_s: Optional[float] = None
