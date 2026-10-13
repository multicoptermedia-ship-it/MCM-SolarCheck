"""Validated local evidence presentation for reviewed pilot reports."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mcm_solarcheck.reporting.report_model import InspectionReport


@dataclass(frozen=True)
class PilotEvidence:
    module: str
    rgb_path: Path | None
    thermal_path: Path | None
    rgb_frame: str | None
    thermal_frame: str | None
    rgb_geometry: str | None
    thermal_geometry: str | None


def local_pilot_evidence(report: InspectionReport) -> tuple[PilotEvidence, ...]:
    if not isinstance(report, InspectionReport):
        raise TypeError("InspectionReport required")
    if report.release_status != "reviewed":
        raise PermissionError("expert review required for image evidence")
    result = []
    for detail in report.details:
        def path_for(image):
            if image is None:
                return None
            path = Path(image.path)
            if path.is_symlink() or not path.is_file():
                raise FileNotFoundError("local evidence image unavailable or symlinked")
            if path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                raise ValueError("unsupported evidence image format")
            return path
        result.append(PilotEvidence(
            detail.module_id, path_for(detail.rgb_image), path_for(detail.thermal_image),
            detail.rgb_image.source_frame_id if detail.rgb_image else None,
            detail.thermal_image.source_frame_id if detail.thermal_image else None,
            detail.rgb_image.geometry_source if detail.rgb_image else None,
            detail.thermal_image.geometry_source if detail.thermal_image else None,
        ))
    return tuple(result)
