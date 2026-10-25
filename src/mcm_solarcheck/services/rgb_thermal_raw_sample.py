"""Read uncalibrated M3T sensor counts inside a validated projected module mask.

No thermal orthomosaic, automatic finding, Celsius conversion, customer data
writes or module confirmation. Only explicit externally validated raw evidence
and complete geometric coverage may pass this diagnostic.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

import numpy as np

from mcm_solarcheck.services.rgb_thermal_module_projection import (
    ThermalProposalMask, MAX_THERMAL_PIXELS,
)
from mcm_solarcheck.thermal.m3t_radiometric import RadiometricRaster


@dataclass(frozen=True)
class ThermalRawModuleSample:
    pixels: int
    minimum_raw: int
    median_raw: float
    maximum_raw: int
    registration_error_px: float
    calibrated_temperature_c: None = None
    module_confirmed: bool = False
    diagnostic_only: bool = True


def sample_uncalibrated_module_raw(
    raster: RadiometricRaster,
    proposal: ThermalProposalMask,
    *,
    raw_extraction_verified: bool,
    maximum_registration_error_px: float = 2.0,
) -> ThermalRawModuleSample:
    """Compute native uint16 *raw-count* summary without image resampling.

    Raw extraction verification must come from a trusted validated adapter,
    never be inferred from a visible color-palette JPEG/MPO or filename. This
    diagnostic is not a Celsius or defect detection result.
    """
    if not isinstance(raster, RadiometricRaster):
        raise TypeError("existing radiometric raster required")
    if not isinstance(proposal, ThermalProposalMask):
        raise TypeError("existing projected thermal proposal mask required")
    if raw_extraction_verified is not True:
        raise ValueError("verified raw extraction required")
    if (
        type(maximum_registration_error_px) not in (int, float)
        or not isfinite(float(maximum_registration_error_px))
        or maximum_registration_error_px <= 0
        or not isfinite(proposal.registration_error_px)
        or not 0 <= proposal.registration_error_px <= maximum_registration_error_px
    ):
        raise ValueError("finite registration error under acceptance bound required")
    if not proposal.usable_for_complete_module_sampling:
        raise ValueError("partial or empty thermal module view must remain unverified")
    if (
        type(raster.width) is not int or type(raster.height) is not int
        or raster.width < 1 or raster.height < 1
        or raster.width * raster.height > MAX_THERMAL_PIXELS
        or raster.byte_order not in ("little", "big")
    ):
        raise ValueError("valid native thermal raster dimensions required")
    if (
        not isinstance(proposal.mask, np.ndarray)
        or proposal.mask.dtype != np.bool_
        or proposal.mask.shape != (raster.height, raster.width)
    ):
        raise ValueError("mask must match original thermal pixel grid")
    if len(raster.samples) != raster.width * raster.height:
        raise ValueError("radiometric sample count does not match raster")
    if any(type(v) is not int or not 0 <= v <= 65535 for v in raster.samples):
        raise ValueError("raw samples must be unsigned 16-bit values")
    counts = np.asarray(raster.samples, dtype=np.uint16).reshape(raster.height, raster.width)
    selected = counts[proposal.mask]
    if not selected.size:
        raise ValueError("projected mask contains no thermal pixel")
    return ThermalRawModuleSample(
        int(selected.size),
        int(selected.min()),
        float(np.median(selected)),
        int(selected.max()),
        float(proposal.registration_error_px),
    )
