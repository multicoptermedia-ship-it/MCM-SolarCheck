"""Read-only, per-frame quantitative analysis of verified 16-bit M3T sensor values.

Computes real sensor-space descriptive statistics. This is NOT an analysis of
PV modules, Celsius calibration, a defect diagnosis, or a completed pipeline.
No image or frame data is persisted. Private frames stay in local memory.
"""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.offline_processing_inventory import (
    capture_offline_processing_inventory,
)
from mcm_solarcheck.services.offline_thermal_raw_check import (
    MAX_RAW_FILE_BYTES, ThermalRawCheckCancelled, _inspect_raw,
    _thermal_entries,
)
from mcm_solarcheck.thermal.analysis import raw_statistics
from mcm_solarcheck.thermal.m3t_radiometric import M3TRadiometricParser


@dataclass(frozen=True)
class ThermalSensorStatisticsResult:
    total: int
    checked: int
    analyzed: int
    without_checksum: int
    issues: int
    varying_frames: int
    constant_frames: int
    minimum_raw_value: int | None
    maximum_raw_value: int | None
    changed_inputs: bool
    read_only: bool = True

    @property
    def valid_for_raw_statistics_only(self) -> bool:
        """Technical pre-analysis quality; NEVER full processing completion."""
        return (
            self.total > 0
            and self.checked == self.analyzed == self.total
            and self.issues == self.without_checksum == 0
            and self.varying_frames + self.constant_frames == self.total
            and not self.changed_inputs
        )


def analyze_imported_thermal_sensor_values(
    database, project_id: str, *, on_progress=None, should_cancel=None,
    maximum_bytes: int = MAX_RAW_FILE_BYTES,
) -> ThermalSensorStatisticsResult:
    """Compute min/mean/median/p95/p99/range for each authenticated frame.

    The individual statistic objects are discarded after each file; the Qt
    client receives *aggregate counts and raw extrema only*, never paths,
    image data, GPS, per-frame readings or private metadata.
    """
    if type(maximum_bytes) is not int or maximum_bytes < 1:
        raise ValueError("positive byte bound required")
    cancelled = should_cancel or (lambda: False)
    if cancelled():
        raise ThermalRawCheckCancelled()
    before = capture_offline_processing_inventory(database, project_id)
    entries = _thermal_entries(database, project_id)
    total = len(entries)
    if before.thermal_frames != total:
        raise ValueError("imported thermal inventory changed during inspection")

    analyzed = unverified = issues = varying = constant = 0
    lowest = highest = None
    parser = M3TRadiometricParser()

    for index, (source, width, height, expected_hash) in enumerate(entries, 1):
        if cancelled():
            raise ThermalRawCheckCancelled()
        frame_statistic = []

        def consume_verified_raster(raster):
            # An input hash must match BEFORE statistics are calculated.
            frame_statistic.append(raw_statistics(raster))

        valid, hash_ok = _inspect_raw(
            source, width, height, expected_hash,
            parser=parser, should_cancel=cancelled,
            maximum_bytes=maximum_bytes,
            on_verified_raster=consume_verified_raster,
        )
        if valid and hash_ok and len(frame_statistic) == 1:
            stats = frame_statistic.pop()
            analyzed += 1
            if stats.dynamic_range:
                varying += 1
            else:
                constant += 1
            lowest = stats.minimum if lowest is None else min(lowest, stats.minimum)
            highest = stats.maximum if highest is None else max(highest, stats.maximum)
        elif valid and not hash_ok:
            # Valid raster but its identity was NOT verified at import.
            unverified += 1
        else:
            issues += 1
        if on_progress is not None:
            on_progress(index, total, issues)
        if cancelled():
            raise ThermalRawCheckCancelled()

    after = capture_offline_processing_inventory(database, project_id)
    return ThermalSensorStatisticsResult(
        total=total, checked=total, analyzed=analyzed,
        without_checksum=unverified, issues=issues,
        varying_frames=varying, constant_frames=constant,
        minimum_raw_value=lowest, maximum_raw_value=highest,
        changed_inputs=before.fingerprint != after.fingerprint,
    )
