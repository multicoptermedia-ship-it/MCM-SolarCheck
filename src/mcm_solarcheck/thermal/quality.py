"""Quality gates for thermal frames before anomaly analysis."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .analysis import RawThermalStatistics, raw_statistics
from .m3t_radiometric import RadiometricRaster


class ThermalQualityGrade(str, Enum):
    PASS = "pass"
    REVIEW = "review"
    REJECT = "reject"


@dataclass(frozen=True)
class ThermalQualityResult:
    grade: ThermalQualityGrade
    reasons: tuple[str, ...]
    statistics: RawThermalStatistics


def assess_raw_thermal_quality(
    raster: RadiometricRaster,
    *,
    expected_width: int = 640,
    expected_height: int = 512,
    minimum_dynamic_range: int = 100,
    saturation_low: int = 0,
    saturation_high: int = 65535,
    max_saturated_fraction: float = 0.001,
) -> ThermalQualityResult:
    """Apply conservative structural/sensor-space quality checks.

    These checks intentionally avoid physical-temperature thresholds. They are
    intended to prevent obviously damaged or degenerate frames from entering
    later PV/anomaly processing.
    """
    stats = raw_statistics(raster)
    reject: list[str] = []
    review: list[str] = []

    if (raster.width, raster.height) != (expected_width, expected_height):
        reject.append(
            f"unexpected raster dimensions {raster.width}x{raster.height}; "
            f"expected {expected_width}x{expected_height}"
        )
    if len(raster.samples) != raster.width * raster.height:
        reject.append("sample count does not match raster dimensions")
    if stats.dynamic_range < minimum_dynamic_range:
        review.append(f"low raw dynamic range: {stats.dynamic_range}")

    saturated = sum(
        1 for value in raster.samples if value <= saturation_low or value >= saturation_high
    )
    fraction = saturated / len(raster.samples)
    if fraction > max_saturated_fraction:
        review.append(f"saturated raw pixel fraction {fraction:.6f} exceeds limit")

    if reject:
        grade = ThermalQualityGrade.REJECT
        reasons = tuple(reject + review)
    elif review:
        grade = ThermalQualityGrade.REVIEW
        reasons = tuple(review)
    else:
        grade = ThermalQualityGrade.PASS
        reasons = ()

    return ThermalQualityResult(grade=grade, reasons=reasons, statistics=stats)
