"""Fast local preflight regression tests; no DJI pixels or network required."""
from pathlib import Path

import pytest

from mcm_solarcheck.services.flight_preflight import (
    FlightPreflightCancelled, scan_dji_flight_preflight,
)


def test_large_dji_folder_inventory_counts_all_entries_with_bounded_memory(tmp_path):
    folder = tmp_path / "flight"
    folder.mkdir()
    for i in range(1200):
        (folder / f"DJI_20261019090000_{i:04d}_V.JPG").write_bytes(b"RGB")
        (folder / f"DJI_20261019090000_{i:04d}_T.JPG").write_bytes(b"TH")
    for i in range(24):
        (folder / f"misc_{i:03d}.txt").write_bytes(b"ignored")
    progress = []
    result = scan_dji_flight_preflight(
        folder, on_progress=progress.append, progress_interval=100,
    )
    assert result.source_folder == folder
    assert result.entries_seen == 2424
    assert result.rgb_files == 1200
    assert result.thermal_files == 1200
    assert result.rgb_bytes == 3600
    assert result.thermal_bytes == 2400
    assert result.other_entries == 24
    assert result.empty_images == 0
    assert result.symlinks == 0
    assert result.inaccessible_entries == 0
    assert result.read_only
    assert not result.image_pixels_decoded
    assert not result.pairing_verified
    assert len(result.issue_examples) <= 8
    assert progress[-1] == 2424
    assert len(progress) <= 25
    assert (folder / "DJI_20261019090000_0001_V.JPG").read_bytes() == b"RGB"


def test_zeros_nonstandard_names_and_symlinks_are_reported_not_imported(tmp_path):
    folder = tmp_path / "flight"
    folder.mkdir()
    (folder / "DJI_1234_V.JPG").write_bytes(b"")
    (folder / "DJI_1234_T.JPG").write_bytes(b"T")
    (folder / "DJI_1234_v.jpg").write_bytes(b"lowercase")
    (folder / "INFO.txt").write_text("ignored")
    (folder / "nested").mkdir()
    target = folder / "DJI_1234_V.JPG"
    try:
        (folder / "linked_V.JPG").symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not supported in this test environment")
    result = scan_dji_flight_preflight(folder)
    assert result.entries_seen == 6
    assert result.rgb_files == 1
    assert result.thermal_files == 1
    assert result.rgb_bytes == 0
    assert result.thermal_bytes == 1
    assert result.empty_images == 1
    assert result.symlinks == 1
    assert result.other_entries == 3
    assert any("Leere Bilddatei" in item for item in result.issue_examples)
    assert any("Namensschreibweise" in item for item in result.issue_examples)


def test_progress_and_cancel_stop_scan_without_touching_sources(tmp_path):
    folder = tmp_path / "flight"
    folder.mkdir()
    for i in range(300):
        (folder / f"frame_{i:04d}_V.JPG").write_bytes(b"unchanged")

    values = []
    with pytest.raises(FlightPreflightCancelled):
        scan_dji_flight_preflight(
            folder, on_progress=values.append,
            should_cancel=lambda: bool(values),
            progress_interval=25,
        )
    assert values == [25]
    assert len(tuple(folder.iterdir())) == 300
    assert (folder / "frame_0000_V.JPG").read_bytes() == b"unchanged"
    with pytest.raises(FlightPreflightCancelled):
        scan_dji_flight_preflight(folder, should_cancel=lambda: True)


@pytest.mark.parametrize("interval,examples", [
    (0, 8), (False, 8), (-2, 8), (1, -1), (1, 33), (1, True),
])
def test_invalid_bounded_scan_options_fail_closed(tmp_path, interval, examples):
    with pytest.raises(ValueError):
        scan_dji_flight_preflight(
            tmp_path, progress_interval=interval, max_issue_examples=examples,
        )


def test_missing_or_symlink_root_rejected_without_following(tmp_path):
    with pytest.raises(ValueError, match="local DJI folder"):
        scan_dji_flight_preflight(tmp_path / "missing")
    (tmp_path / "file").write_bytes(b"source")
    with pytest.raises(ValueError, match="local DJI folder"):
        scan_dji_flight_preflight(tmp_path / "file")
    try:
        (tmp_path / "link").symlink_to(tmp_path, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not supported in this test environment")
    with pytest.raises(ValueError, match="local DJI folder"):
        scan_dji_flight_preflight(tmp_path / "link")


def test_diagnostic_examples_are_bounded_even_for_many_empty_images(tmp_path):
    for i in range(125):
        (tmp_path / f"DJI_1234_{i:04d}_V.JPG").write_bytes(b"")
    result = scan_dji_flight_preflight(tmp_path, max_issue_examples=3)
    assert result.empty_images == 125
    assert result.rgb_files == 125
    assert len(result.issue_examples) == 3
    result_without_examples = scan_dji_flight_preflight(
        tmp_path, max_issue_examples=0,
    )
    assert result_without_examples.empty_images == 125
    assert result_without_examples.issue_examples == ()
