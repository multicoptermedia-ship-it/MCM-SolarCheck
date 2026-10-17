"""Synthetic ZIP-only checks: never commit real inspection imagery."""
from zipfile import ZipFile

import pytest

from mcm_solarcheck.services.flight_zip_preflight import inspect_dji_flight_zip


def _zip(tmp_path, names):
    path = tmp_path / "flight.zip"
    with ZipFile(path, "w") as archive:
        for name in names:
            archive.writestr(name, b"synthetic")
    return path


def test_same_timestamp_pair_is_accepted_without_geometry_approval(tmp_path):
    result = inspect_dji_flight_zip(_zip(tmp_path, [
        "DJI_20260725154422_0001_T.JPG", "DJI_20260725154422_0001_V.JPG",
    ]))
    assert (result.rgb_count, result.thermal_count, result.paired_count) == (1, 1, 1)
    assert not result.mismatched_timestamps
    assert result.ready_for_geometry is False


def test_different_days_are_rejected_as_pairs(tmp_path):
    result = inspect_dji_flight_zip(_zip(tmp_path, [
        "DJI_20260625154422_0001_T.JPG", "DJI_20260725154422_0001_V.JPG",
    ]))
    assert result.paired_count == 0
    assert result.mismatched_timestamps == ("0001",)


def test_unpaired_and_duplicate_frames(tmp_path):
    result = inspect_dji_flight_zip(_zip(tmp_path, ["DJI_20260725154422_0001_T.JPG"]))
    assert result.unpaired_ids == ("0001",)
    with pytest.raises(ValueError, match="duplicate"):
        inspect_dji_flight_zip(_zip(tmp_path, [
            "a/DJI_20260725154422_0001_T.JPG",
            "b/DJI_20260725154422_0001_T.JPG",
        ]))


def test_zip_slip_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="unsafe"):
        inspect_dji_flight_zip(_zip(tmp_path, ["../DJI_20260725154422_0001_T.JPG"]))
