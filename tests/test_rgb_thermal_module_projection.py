"""Synthetic proof of an unconfirmed RGB-to-native-thermal proposal workflow."""
from __future__ import annotations

import numpy as np
import pytest

from mcm_solarcheck.pairing.geometry import PixelTransform
from mcm_solarcheck.services.rgb_thermal_module_projection import (
    project_rgb_proposal_to_thermal, rasterize_projected_thermal_proposal,
)
from mcm_solarcheck.services.rgb_thermal_raw_sample import sample_uncalibrated_module_raw
from mcm_solarcheck.thermal.m3t_radiometric import RadiometricRaster

RGB_SIZE = (4000, 3000)
THERMAL_SIZE = (640, 512)
POLYGON = ((200.0, 200.0), (400.0, 200.0), (400.0, 360.0), (200.0, 360.0))


def transform(matrix=None, *, error=0.35, method="calibrated_homography", validated=True):
    return PixelTransform(
        method, validated, *RGB_SIZE, *THERMAL_SIZE,
        matrix or ((0.12, 0, 20), (0, 0.14, 10), (0, 0, 1)),
        error,
    )


def test_independent_projected_mask_stays_on_native_thermal_grid():
    original = tuple(POLYGON)
    h = transform()
    projected = project_rgb_proposal_to_thermal(POLYGON, h)
    assert projected.points_xy[0] == pytest.approx((44.0, 38.0))
    assert (projected.width, projected.height) == THERMAL_SIZE
    mask = rasterize_projected_thermal_proposal(projected)
    assert mask.mask.shape == (512, 640)
    assert mask.mask.dtype == np.bool_
    assert mask.usable_for_complete_module_sampling
    assert mask.area_coverage_fraction == pytest.approx(1.0)
    assert mask.pixels > 0
    assert POLYGON == original
    assert projected.status == "unconfirmed_module_proposal"


@pytest.mark.parametrize("bad", [
    transform(validated=False),
    transform(method="resolution_ratio"),
    transform(method="unvalidated"),
    transform(error=None),
    transform(error=4.0),
    transform(error=float("nan")),
    transform(matrix=((0.12, 0, 20), (0, 0.14, 10), (0, 0, 0))),
    transform(matrix=((1, 0, 0), (0, 0, 0), (0, 0, 1))),
    transform(matrix=((1, 0, 0), (0, 1, 0), (0.01, 0, -3))),
])
def test_must_reject_unverified_ratio_degenerate_and_unsafe_transforms(bad):
    with pytest.raises(ValueError):
        project_rgb_proposal_to_thermal(POLYGON, bad)


@pytest.mark.parametrize("polygon", [
    ((200, 200), (400, 200), (200, 300)),
    ((200, 200), (300, 300), (200, 300), (300, 200)),
    ((-1, 200), (400, 200), (400, 300), (0, 300)),
    ((200, 200), (4000, 200), (4000, 300), (200, 300)),
    ((200, 200), (400, 200), (400, float("inf")), (200, 300)),
])
def test_invalid_and_outside_rgb_proposals_fail_closed(polygon):
    with pytest.raises(ValueError):
        project_rgb_proposal_to_thermal(polygon, transform())


def test_partial_thermal_view_cannot_be_sampled_as_complete_module():
    h = transform(matrix=((0.20, 0, -50), (0, 0.20, 0), (0, 0, 1)))
    projection = project_rgb_proposal_to_thermal(POLYGON, h)
    mask = rasterize_projected_thermal_proposal(projection)
    assert 0 < mask.area_coverage_fraction < 0.99
    assert mask.pixels > 0
    assert not mask.usable_for_complete_module_sampling
    raster = RadiometricRaster(640, 512, "little", (1200,) * (640 * 512), 0)
    with pytest.raises(ValueError, match="partial"):
        sample_uncalibrated_module_raw(raster, mask, raw_extraction_verified=True)


def test_projected_proposal_outside_thermal_frame_has_zero_coverage():
    h = transform(matrix=((0.20, 0, -150), (0, 0.20, 0), (0, 0, 1)))
    mask = rasterize_projected_thermal_proposal(project_rgb_proposal_to_thermal(POLYGON, h))
    assert mask.pixels == 0
    assert mask.area_coverage_fraction == 0
    assert not mask.usable_for_complete_module_sampling


def test_raw_sample_is_only_uncalibrated_sensor_counts_not_celsius():
    mask = rasterize_projected_thermal_proposal(
        project_rgb_proposal_to_thermal(POLYGON, transform())
    )
    samples = (1200,) * (640 * 512)
    raster = RadiometricRaster(640, 512, "little", samples, 0)
    result = sample_uncalibrated_module_raw(
        raster, mask, raw_extraction_verified=True,
    )
    assert result.pixels == mask.pixels
    assert (result.minimum_raw, result.median_raw, result.maximum_raw) == (1200, 1200, 1200)
    assert result.calibrated_temperature_c is None
    assert result.module_confirmed is False
    assert result.diagnostic_only is True
    assert samples[0] == 1200


def test_raw_unverified_and_dimension_mismatch_rejected():
    mask = rasterize_projected_thermal_proposal(
        project_rgb_proposal_to_thermal(POLYGON, transform())
    )
    raster = RadiometricRaster(640, 512, "little", (1000,) * (640 * 512), 0)
    with pytest.raises(ValueError, match="extraction"):
        sample_uncalibrated_module_raw(raster, mask, raw_extraction_verified=False)
    wrong_dimensions = RadiometricRaster(512, 640, "little", raster.samples, 0)
    with pytest.raises(ValueError, match="original thermal pixel grid"):
        sample_uncalibrated_module_raw(
            wrong_dimensions, mask, raw_extraction_verified=True,
        )
    with pytest.raises(ValueError, match="registration"):
        sample_uncalibrated_module_raw(
            raster, mask, raw_extraction_verified=True, maximum_registration_error_px=0.1,
        )


def test_unverified_legacy_transform_is_not_a_mask_or_radiometry_gate():
    from mcm_solarcheck.pairing.geometry import unavailable_transform

    with pytest.raises(ValueError, match="independently validated"):
        project_rgb_proposal_to_thermal(POLYGON, unavailable_transform())
