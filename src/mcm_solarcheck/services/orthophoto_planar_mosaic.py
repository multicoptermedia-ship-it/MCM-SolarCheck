"""Conservative native orthophoto mosaic assembly for surveyed planar frames."""
from __future__ import annotations

from pathlib import Path
import numpy as np

from mcm_solarcheck.services.orthophoto_planar_rectification import SurveyedFrame, rectify_planar_frame
from mcm_solarcheck.services.orthomosaic_geotiff_contract import GeoTIFFSpatialReference


def build_planar_orthophoto(
    frames: tuple[SurveyedFrame, ...],
    reference: GeoTIFFSpatialReference,
    *,
    thermal: bool = False,
    max_pixels: int = 24_000_000,
):
    """Generate RGB or thermal grid from photographs; reject incomplete coverage.

    This is a controlled planar workflow, not a general terrain orthomosaic.
    Thermal pixel values are uncalibrated unless separately established.
    """
    if not frames or len(frames) > 1000:
        raise ValueError("one to 1000 surveyed photographs are required")
    if reference.width * reference.height > max_pixels:
        raise ValueError("orthophoto output exceeds configured pixel limit")
    output = None
    covered = np.zeros((reference.height, reference.width), dtype=bool)
    for frame in frames:
        image, mask = rectify_planar_frame(frame, reference)
        if thermal:
            if image.ndim == 3:
                raise ValueError("thermal source must be single-band, without false-color RGB")
        else:
            if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
                raise ValueError("RGB source must be 8-bit three-channel")
            image = image[:, :, ::-1]  # OpenCV BGR -> GeoTIFF RGB
        if output is None:
            output = np.zeros_like(image)
        if image.shape != output.shape or image.dtype != output.dtype:
            raise ValueError("orthophoto frame formats differ")
        new = mask & ~covered
        output[new] = image[new]
        covered |= mask
    if not covered.all():
        raise ValueError("surveyed frames do not cover the entire requested GIS extent")
    return output
