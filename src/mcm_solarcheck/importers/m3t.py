"""Integrated DJI M3T thermal import pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from mcm_solarcheck.domain.models import Finding, ThermalFrame
from mcm_solarcheck.thermal.analysis import RawAnomalyCandidate, hottest_raw_candidates
from mcm_solarcheck.thermal.findings import candidates_to_findings
from mcm_solarcheck.thermal.m3t_radiometric import M3TRadiometricParser, RadiometricRaster
from mcm_solarcheck.thermal.quality import ThermalQualityResult, assess_raw_thermal_quality
from .m3t_xmp import M3TXmpMetadata, parse_m3t_xmp

_SEQUENCE_RE = re.compile(r"_(\d{4})_T\.JPG$", re.IGNORECASE)


@dataclass(frozen=True)
class M3TImportResult:
    frame: ThermalFrame
    raster: RadiometricRaster
    quality: ThermalQualityResult
    candidates: tuple[RawAnomalyCandidate, ...]
    findings: tuple[Finding, ...]
    xmp: M3TXmpMetadata


class M3TImporter:
    """Turn one M3T thermal R-JPEG/MPO into review-ready domain data."""

    def __init__(self, parser: M3TRadiometricParser | None = None) -> None:
        self.parser = parser or M3TRadiometricParser()

    @staticmethod
    def frame_id(path: Path) -> str:
        match = _SEQUENCE_RE.search(path.name)
        return f"T-{match.group(1)}" if match else f"T-{path.stem}"

    def import_file(
        self,
        path: str | Path,
        *,
        candidate_percentile: float = 99.9,
        candidate_limit: int = 100,
    ) -> M3TImportResult:
        source = Path(path)
        data = source.read_bytes()
        raster = self.parser.parse_bytes(data)
        xmp = parse_m3t_xmp(data)
        quality = assess_raw_thermal_quality(raster)

        frame = ThermalFrame(
            frame_id=self.frame_id(source),
            source_file=source,
            camera_make=xmp.camera_make,
            camera_model=xmp.camera_model,
            width=raster.width,
            height=raster.height,
            timestamp_utc=xmp.timestamp_utc,
            position=xmp.position,
            camera_pose=xmp.camera_pose,
            flight_pose=xmp.flight_pose,
            rtk=xmp.rtk,
            metadata=dict(xmp.raw),
            thermal_width=raster.width,
            thermal_height=raster.height,
            thermal_source="DJI M3T APP3 raw",
            temperature_matrix=None,
        )

        # Candidate generation remains raw-space only. Reject frames do not
        # generate findings; review/pass frames may proceed to expert review.
        candidates = () if quality.grade.value == "reject" else hottest_raw_candidates(
            raster,
            percentile=candidate_percentile,
            limit=candidate_limit,
        )
        findings = candidates_to_findings(candidates, frame)
        return M3TImportResult(frame, raster, quality, candidates, findings, xmp)
