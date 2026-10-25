"""Coverage diagnostics remain non-metric and count-only."""
from dataclasses import replace
import numpy as np
import pytest

from mcm_solarcheck.services.module_plane_rectification import ModuleSurfaceGrid
from mcm_solarcheck.services.rgb_surface_tile_render import RGBRenderedSurfaceTile
from mcm_solarcheck.services.rgb_surface_tile_audit import audit_rgb_surface_tile
from mcm_solarcheck.services.rgb_surface_tiles import RGBSurfaceTile


def tile(mask):
    valid = np.asarray(mask, dtype=bool)
    h, w = valid.shape
    grid = ModuleSurfaceGrid(0, 0, .1, w, h)
    return RGBRenderedSurfaceTile(
        RGBSurfaceTile(0, 1, grid),
        np.zeros((h, w, 3), dtype=np.uint8),
        valid, int(np.count_nonzero(valid)),
    )


@pytest.mark.parametrize("mask,state,fraction", [
    ([[False, False], [False, False]], "empty", 0.),
    ([[True, False], [True, False]], "partial", .5),
    ([[True, True], [True, True]], "covered_unverified", 1.),
])
def test_coverage_audit_never_claims_verified_orthophoto(mask, state, fraction):
    audit = audit_rgb_surface_tile(tile(mask))
    assert audit.state == state
    assert audit.covered_fraction == fraction
    assert audit.covered_pixels + audit.missing_pixels == 4
    assert audit.column == 1
    assert not audit.independent_survey_verified
    assert not audit.photogrammetric_orthophoto_verified


def test_mismatching_data_and_mask_rejected():
    t = tile([[True, False], [True, False]])
    with pytest.raises(ValueError, match="inconsistent"):
        audit_rgb_surface_tile(replace(t, covered_pixels=0))
    with pytest.raises(ValueError, match="match"):
        audit_rgb_surface_tile(replace(t, valid_mask=np.ones((1, 4), dtype=bool)))
