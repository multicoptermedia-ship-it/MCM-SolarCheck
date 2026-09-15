"""DJI Mavic 3 Thermal XMP metadata reader.

Maps DJI-specific XMP attributes into vendor-neutral domain models. The parser
uses the XMP packet embedded in the JPEG/MPO and does not depend on DJI SDKs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Mapping

from mcm_solarcheck.domain.models import Pose, Position, RTKQuality


_XMP_RE = re.compile(rb"<\?xpacket\b.*?</x:xmpmeta>", re.DOTALL)
_ATTR_RE = re.compile(r'(?:[\w-]+:)?([\w-]+)="([^"]*)"')


@dataclass(frozen=True)
class M3TXmpMetadata:
    timestamp_utc: datetime | None
    position: Position | None
    camera_pose: Pose
    flight_pose: Pose
    rtk: RTKQuality
    camera_make: str | None
    camera_model: str | None
    image_source: str | None
    raw: Mapping[str, str]


def _float(values: Mapping[str, str], key: str) -> float | None:
    value = values.get(key)
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_m3t_xmp(data: bytes) -> M3TXmpMetadata:
    match = _XMP_RE.search(data)
    if not match:
        raise ValueError("No XMP packet found in image")
    text = match.group(0).decode("utf-8", errors="replace")
    values = {key: value for key, value in _ATTR_RE.findall(text)}

    lat = _float(values, "GpsLatitude")
    lon = _float(values, "GpsLongitude")
    altitude = _float(values, "AbsoluteAltitude")
    position = None if lat is None or lon is None else Position(lat, lon, altitude)

    camera_pose = Pose(
        yaw_deg=_float(values, "GimbalYawDegree"),
        pitch_deg=_float(values, "GimbalPitchDegree"),
        roll_deg=_float(values, "GimbalRollDegree"),
    )
    flight_pose = Pose(
        yaw_deg=_float(values, "FlightYawDegree"),
        pitch_deg=_float(values, "FlightPitchDegree"),
        roll_deg=_float(values, "FlightRollDegree"),
    )
    rtk = RTKQuality(
        status=values.get("GpsStatus"),
        std_lat_m=_float(values, "RtkStdLat"),
        std_lon_m=_float(values, "RtkStdLon"),
        std_height_m=_float(values, "RtkStdHgt"),
        correction_age_s=_float(values, "RtkDiffAge"),
        altitude_type=values.get("AltitudeType"),
    )

    return M3TXmpMetadata(
        timestamp_utc=_timestamp(values.get("UTCAtExposure")),
        position=position,
        camera_pose=camera_pose,
        flight_pose=flight_pose,
        rtk=rtk,
        camera_make=values.get("Make"),
        camera_model=values.get("Model") or values.get("DroneModel"),
        image_source=values.get("ImageSource"),
        raw=values,
    )
