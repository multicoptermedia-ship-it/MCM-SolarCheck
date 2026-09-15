"""Vendor-neutral analysis for validated raw thermal rasters.

Raw M3T samples are deliberately analysed in sensor-value space. Thresholds
are relative to the local image distribution; no Celsius claim is made until
a validated temperature provider is available.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from statistics import fmean, median

from .m3t_radiometric import RadiometricRaster


@dataclass(frozen=True)
class RawThermalStatistics:
    minimum: int
    maximum: int
    mean: float
    median: float
    p95: float
    p99: float
    dynamic_range: int


@dataclass(frozen=True)
class RawAnomalyCandidate:
    x: int
    y: int
    raw_value: int
    delta_from_median: float
    percentile_threshold: float


def _percentile(sorted_values: tuple[int, ...], percentile: float) -> float:
    if not sorted_values:
        raise ValueError("Cannot calculate percentile of empty raster")
    if not 0.0 <= percentile <= 100.0:
        raise ValueError("percentile must be between 0 and 100")
    index = max(0, min(len(sorted_values) - 1, ceil(percentile / 100 * len(sorted_values)) - 1))
    return float(sorted_values[index])


def raw_statistics(raster: RadiometricRaster) -> RawThermalStatistics:
    values = raster.samples
    if not values:
        raise ValueError("Raster contains no samples")
    ordered = tuple(sorted(values))
    minimum = ordered[0]
    maximum = ordered[-1]
    return RawThermalStatistics(
        minimum=minimum,
        maximum=maximum,
        mean=fmean(values),
        median=float(median(values)),
        p95=_percentile(ordered, 95),
        p99=_percentile(ordered, 99),
        dynamic_range=maximum - minimum,
    )


def hottest_raw_candidates(
    raster: RadiometricRaster,
    *,
    percentile: float = 99.9,
    minimum_delta_from_median: float = 0.0,
    limit: int = 100,
) -> tuple[RawAnomalyCandidate, ...]:
    """Return hottest raw pixels as *candidates*, not defect classifications.

    This is useful before Celsius conversion is available because ordering and
    local contrast remain meaningful in raw sensor space. Later stages should
    constrain candidates to PV-module masks and use calibrated temperatures.
    """
    if limit < 1:
        raise ValueError("limit must be >= 1")
    ordered = tuple(sorted(raster.samples))
    threshold = _percentile(ordered, percentile)
    med = float(median(raster.samples))

    candidates: list[RawAnomalyCandidate] = []
    for index, value in enumerate(raster.samples):
        delta = value - med
        if value >= threshold and delta >= minimum_delta_from_median:
            y, x = divmod(index, raster.width)
            candidates.append(
                RawAnomalyCandidate(
                    x=x,
                    y=y,
                    raw_value=value,
                    delta_from_median=delta,
                    percentile_threshold=threshold,
                )
            )

    candidates.sort(key=lambda item: (-item.raw_value, item.y, item.x))
    return tuple(candidates[:limit])
