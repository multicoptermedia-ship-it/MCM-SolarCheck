"""GIS metadata validation; never infer georeferencing from RGB previews."""
import pytest

from mcm_solarcheck.services.orthomosaic_geotiff_contract import (
    GeoTIFFSpatialReference, require_geotiff_export_target,
    validate_geotiff_reference,
)


def reference(**overrides):
    data = dict(crs="EPSG:25832", transform=(0.05, 0.0, 350000.0, 0.0, -0.05, 5650000.0),
                width=1024, height=512, nodata=None)
    data.update(overrides)
    return GeoTIFFSpatialReference(**data)


def test_valid_gis_reference_and_target(tmp_path):
    target = require_geotiff_export_target(tmp_path / "ortho.tif", reference())
    assert target.name == "ortho.tif"
    assert not target.exists()


@pytest.mark.parametrize("changes", [
    {"crs": ""}, {"width": 0}, {"height": -1},
    {"transform": (0., 0., 1., 0., 0., 2.)},
    {"transform": (float("nan"), 0., 1., 0., -1., 2.)},
    {"nodata": float("inf")},
])
def test_invalid_reference_fails_closed(changes):
    with pytest.raises(ValueError):
        validate_geotiff_reference(reference(**changes))


def test_target_must_be_tiff_and_must_not_overwrite(tmp_path):
    with pytest.raises(ValueError, match="GeoTIFF target"):
        require_geotiff_export_target(tmp_path / "preview.png", reference())
    existing = tmp_path / "ortho.tiff"
    existing.write_bytes(b"not a geotiff")
    with pytest.raises(FileExistsError):
        require_geotiff_export_target(existing, reference())
