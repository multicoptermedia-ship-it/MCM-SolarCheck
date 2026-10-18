"""ODM staging tests: no image resampling and no silent frame omission."""
import pytest

from mcm_solarcheck.services.odm_rgb_adapter import (
    prepare_odm_rgb_inputs, stage_odm_rgb_project,
)


def test_thousand_capture_rgb_staging_preserves_bytes(tmp_path):
    flight = tmp_path / "flight"
    flight.mkdir()
    for i in range(1000):
        (flight / f"DJI_20260725154421_{i:04d}_V.JPG").write_bytes(b"rgb" + str(i).encode())
        (flight / f"DJI_20260725154421_{i:04d}_T.JPG").write_bytes(b"thermal" + str(i).encode())
    result = stage_odm_rgb_project(flight, tmp_path / "odm-project")
    assert len(result["images"]) == 1000
    assert not result["missing_rgb"]
    for i in (0, 499, 999):
        filename = f"DJI_20260725154421_{i:04d}_V.JPG"
        assert (tmp_path / "odm-project" / "images" / filename).read_bytes() == (
            flight / filename
        ).read_bytes()


def test_missing_rgb_is_explicit(tmp_path):
    (tmp_path / "DJI_20260725154421_0001_T.JPG").write_bytes(b"thermal")
    (tmp_path / "DJI_20260725154421_0002_V.JPG").write_bytes(b"rgb")
    result = prepare_odm_rgb_inputs(tmp_path)
    assert len(result["rgb"]) == 1
    assert result["missing_rgb"] == ("20260725154421_0001",)


def test_capture_limit_fails_before_staging(tmp_path):
    for i in range(3):
        (tmp_path / f"DJI_20260725154421_{i:04d}_V.JPG").write_bytes(b"rgb")
    with pytest.raises(ValueError, match="capture limit"):
        stage_odm_rgb_project(tmp_path, tmp_path / "odm-project", max_captures=2)
    assert not (tmp_path / "odm-project").exists()
