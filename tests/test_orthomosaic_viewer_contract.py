"""Viewer contract tests: no unregistered or remote imagery can be displayed."""
import pytest

from mcm_solarcheck.services.orthomosaic_viewer_contract import (
    OrthomosaicLayer,
    RegisteredOrthomosaicPair,
)


def layers():
    return (
        OrthomosaicLayer("/api/projects/p1/ortho/rgb", 4096, 3072, "rgb_orthomosaic"),
        OrthomosaicLayer("/api/projects/p1/ortho/thermal", 4096, 3072, "thermal_visualization"),
    )


def make_pair(**kwargs):
    rgb, thermal = layers()
    data = dict(
        project_id="p1", rgb=rgb, thermal=thermal,
        registration_verified=True, coordinate_system="EPSG:32632",
        registration_reference="verified-registration-1",
    )
    data.update(kwargs)
    return RegisteredOrthomosaicPair(**data)


def test_verified_pair_serializes_without_temperature_claim():
    manifest = make_pair().to_viewer_manifest()
    assert manifest["registration_verified"] is True
    assert manifest["thermal_is_visualization_only"] is True
    assert manifest["width"] == 4096
    assert manifest["rgb_url"].startswith("/")


@pytest.mark.parametrize("overrides", [
    {"registration_verified": False},
    {"registration_reference": ""},
    {"coordinate_system": ""},
    {"project_id": ""},
    {"thermal": OrthomosaicLayer("/thermal", 512, 512, "thermal_visualization")},
    {"rgb": OrthomosaicLayer("https://example.org/rgb", 4096, 3072, "rgb_orthomosaic")},
    {"rgb": OrthomosaicLayer("//example.org/rgb", 4096, 3072, "rgb_orthomosaic")},
    {"thermal": OrthomosaicLayer("/thermal", 4096, 3072, "rgb_orthomosaic")},
    {"rgb": OrthomosaicLayer("/rgb", 0, 3072, "rgb_orthomosaic")},
])
def test_invalid_viewer_manifest_fails_closed(overrides):
    with pytest.raises(ValueError):
        make_pair(**overrides)
