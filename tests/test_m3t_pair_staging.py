"""Synthetic archive tests: never commit real customer images."""
from zipfile import ZipFile

import pytest

from mcm_solarcheck.importers.m3t_pair_selection import select_m3t_pairs
from mcm_solarcheck.importers.m3t_pair_staging import stage_m3t_pairs


def make_archive(path, suffix, count):
    with ZipFile(path, "w") as archive:
        for i in range(1, count + 1):
            archive.writestr(f"DJI_20250825121339_{i:04d}_{suffix}.JPG", b"synthetic")


def test_select_29_from_36_thermal_and_29_rgb(tmp_path):
    t, v = tmp_path / "t.zip", tmp_path / "v.zip"
    make_archive(t, "T", 36)
    make_archive(v, "V", 29)
    selection = select_m3t_pairs(t, v)
    assert len(selection.sequences) == 29
    assert selection.sequences[-1] == "0029"
    assert not any("_0030_" in name for name in selection.thermal_names)
    destination = tmp_path / "staged"
    destination.mkdir()
    stage_m3t_pairs(t, v, destination)
    assert len(list(destination.iterdir())) == 58
    assert not (destination / "DJI_20250825121339_0030_T.JPG").exists()


def test_missing_pair_fails_closed(tmp_path):
    t, v = tmp_path / "t.zip", tmp_path / "v.zip"
    make_archive(t, "T", 36)
    make_archive(v, "V", 28)
    with pytest.raises(ValueError, match="lacks"):
        select_m3t_pairs(t, v)


def test_destination_must_be_empty(tmp_path):
    t, v = tmp_path / "t.zip", tmp_path / "v.zip"
    make_archive(t, "T", 29)
    make_archive(v, "V", 29)
    destination = tmp_path / "staged"
    destination.mkdir()
    (destination / "existing").write_text("preserve")
    with pytest.raises(ValueError, match="empty"):
        stage_m3t_pairs(t, v, destination)
    assert (destination / "existing").read_text() == "preserve"


def test_traversal_is_rejected(tmp_path):
    t, v = tmp_path / "t.zip", tmp_path / "v.zip"
    with ZipFile(t, "w") as archive:
        archive.writestr("../DJI_20250825121339_0001_T.JPG", b"unsafe")
    make_archive(v, "V", 29)
    with pytest.raises(ValueError, match="unsafe"):
        select_m3t_pairs(t, v)
