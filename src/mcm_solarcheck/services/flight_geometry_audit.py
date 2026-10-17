"""Local DJI XMP camera-reference audit without exporting private coordinates."""
from __future__ import annotations
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath
from zipfile import ZipFile
import re
import xml.etree.ElementTree as ET

from mcm_solarcheck.services.flight_zip_preflight import inspect_dji_flight_zip

_PATTERN = re.compile(r"DJI_\d{14}_\d{4}_([TV])\.JPG", re.IGNORECASE)


@dataclass(frozen=True)
class FlightGeometryAudit:
    rgb_count: int
    thermal_count: int
    rgb_sources: tuple[str, ...]
    thermal_sources: tuple[str, ...]
    rgb_gps_statuses: tuple[str, ...]
    thermal_gps_statuses: tuple[str, ...]
    missing_pose_count: int
    diagnostics: tuple[str, ...]

    @property
    def ready_for_metric_orthophoto(self) -> bool:
        return False


def audit_dji_flight_geometry(path, *, max_image_bytes=80_000_000):
    """Inspect DJI XMP metadata locally; never infer surveyed roof/camera geometry."""
    from PIL import Image
    inspect_dji_flight_zip(path)
    counts = {"V": 0, "T": 0}
    sources = {"V": set(), "T": set()}
    statuses = {"V": set(), "T": set()}
    altitude_types = {"V": set(), "T": set()}
    missing = 0
    with ZipFile(path) as archive:
        for item in archive.infolist():
            match = _PATTERN.fullmatch(PurePosixPath(item.filename).name)
            if item.is_dir() or match is None:
                continue
            modality = match.group(1).upper()
            if item.file_size > max_image_bytes:
                raise ValueError("DJI image exceeds XMP inspection limit")
            with archive.open(item) as stream:
                payload = stream.read(max_image_bytes + 1)
            if len(payload) > max_image_bytes:
                raise ValueError("DJI image exceeds XMP inspection limit")
            with Image.open(BytesIO(payload)) as image:
                xmp = image.info.get("xmp")
            if not xmp:
                missing += 1
                continue
            try:
                root = ET.fromstring(xmp.strip())
            except ET.ParseError as error:
                raise ValueError("malformed DJI XMP metadata") from error
            description = next((node for node in root.iter() if node.tag.endswith("}Description")), None)
            if description is None:
                missing += 1
                continue
            values = {key.rsplit("}", 1)[-1]: value for key, value in description.attrib.items()}
            counts[modality] += 1
            sources[modality].add(values.get("ImageSource", "missing"))
            statuses[modality].add(values.get("GpsStatus", "missing"))
            altitude_types[modality].add(values.get("AltitudeType", "missing"))
            required = ("GimbalPitchDegree", "GimbalRollDegree", "GimbalYawDegree", "GpsLatitude", "GpsLongitude")
            try:
                import math
                if not all(math.isfinite(float(values[key])) for key in required):
                    missing += 1
            except (KeyError, ValueError, TypeError):
                missing += 1
    diagnostics = ["DJI gimbal angles do not establish roof inclination or verified ENU camera rotation"]
    if statuses["V"] != statuses["T"] or altitude_types["V"] != altitude_types["T"]:
        diagnostics.append("RGB and thermal position/altitude reference conventions differ; do not combine unverified")
    if missing:
        diagnostics.append("some images lack complete finite pose metadata")
    diagnostics.append("independent camera calibration and surveyed roof plane required")
    return FlightGeometryAudit(
        counts["V"], counts["T"], tuple(sorted(sources["V"])), tuple(sorted(sources["T"])),
        tuple(sorted(statuses["V"])), tuple(sorted(statuses["T"])), missing, tuple(diagnostics),
    )
