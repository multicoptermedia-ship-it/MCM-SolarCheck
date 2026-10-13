"""Build a conservative evidence index without loading or copying customer images."""
from __future__ import annotations

from dataclasses import dataclass
from mcm_solarcheck.reporting.report_model import InspectionReport


@dataclass(frozen=True)
class EvidenceReference:
    module: str
    rgb_frame: str | None
    thermal_frame: str | None
    rgb_geometry: str | None
    thermal_geometry: str | None


def evidence_index(report: InspectionReport) -> tuple[EvidenceReference, ...]:
    if not isinstance(report, InspectionReport):
        raise TypeError("InspectionReport required")
    if report.release_status != "reviewed":
        raise PermissionError("evidence index requires reviewed report")
    return tuple(
        EvidenceReference(
            module=detail.module_id,
            rgb_frame=detail.rgb_image.source_frame_id if detail.rgb_image else None,
            thermal_frame=detail.thermal_image.source_frame_id if detail.thermal_image else None,
            rgb_geometry=detail.rgb_image.geometry_source if detail.rgb_image else None,
            thermal_geometry=detail.thermal_image.geometry_source if detail.thermal_image else None,
        )
        for detail in report.details
    )
