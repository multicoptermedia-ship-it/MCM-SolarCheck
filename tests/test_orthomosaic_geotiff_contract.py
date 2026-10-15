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


def test_world_corners_follow_declared_affine_reference():
    from mcm_solarcheck.services.orthomosaic_geotiff_contract import geotiff_world_corners
    corners = geotiff_world_corners(reference(width=2, height=3,
        transform=(2., 0., 100., 0., -4., 200.)))
    assert corners == ((100., 200.), (104., 200.), (104., 188.), (100., 188.))


def test_rotated_geotiff_footprint_is_not_assumed_axis_aligned():
    from mcm_solarcheck.services.orthomosaic_geotiff_contract import geotiff_world_corners
    corners = geotiff_world_corners(reference(width=2, height=3,
        transform=(2., 1., 100., -1., -4., 200.)))
    assert corners == ((100., 200.), (104., 198.), (107., 186.), (103., 188.))


def test_geotiff_writer_requires_explicit_verified_georeferencing(tmp_path):
    import numpy as np
    from mcm_solarcheck.services.orthomosaic_geotiff_contract import (
        write_georeferenced_rgb_geotiff,
    )
    rgb = np.zeros((3, 2, 3), dtype=np.uint8)
    ref = reference(width=2, height=3)
    with pytest.raises(ValueError, match="verified georeferencing"):
        write_georeferenced_rgb_geotiff(rgb, tmp_path / "unsafe.tif", ref)
    assert not (tmp_path / "unsafe.tif").exists()


def test_geotiff_writer_roundtrips_in_rasterio(tmp_path):
    import numpy as np
    import rasterio
    from mcm_solarcheck.services.orthomosaic_geotiff_contract import (
        write_georeferenced_rgb_geotiff,
    )
    rgb = np.zeros((3, 2, 3), dtype=np.uint8)
    rgb[1, 0] = [25, 100, 200]
    ref = reference(width=2, height=3)
    target = write_georeferenced_rgb_geotiff(
        rgb, tmp_path / "verified.tif", ref, georeferencing_verified=True,
    )
    with rasterio.open(target) as dataset:
        assert dataset.driver == "GTiff"
        assert dataset.crs.to_epsg() == 25832
        assert tuple(dataset.transform)[:6] == ref.transform
        assert (dataset.width, dataset.height, dataset.count) == (2, 3, 3)
        assert [dataset.read(i)[1, 0] for i in (1, 2, 3)] == [25, 100, 200]


def test_geotiff_writer_rejects_bad_raster_before_creating_file(tmp_path):
    import numpy as np
    from mcm_solarcheck.services.orthomosaic_geotiff_contract import (
        write_georeferenced_rgb_geotiff,
    )
    ref = reference(width=2, height=3)
    target = tmp_path / "bad.tif"
    for image in (
        np.zeros((2, 3, 3), dtype=np.uint8),
        np.zeros((3, 2, 3), dtype=np.float32),
        np.zeros((3, 2), dtype=np.uint8),
    ):
        with pytest.raises(ValueError, match="raster"):
            write_georeferenced_rgb_geotiff(
                image, target, ref, georeferencing_verified=True,
            )
        assert not target.exists()
