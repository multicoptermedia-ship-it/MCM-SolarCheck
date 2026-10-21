"""Synthetic ZIP fixtures only: never copy user-provided plant photos into Git."""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import zipfile

import pytest
from PIL import Image

from mcm_solarcheck.importers.m3t_original_archive_audit import (
    audit_original_m3t_archives,
)
from mcm_solarcheck.importers.m3t_original_zip_staging import (
    stage_original_m3t_archives,
)


@pytest.fixture(scope="module")
def synthetic_jpegs():
    def make(size):
        image = Image.new("RGB", size, color=(30, 90, 70))
        exif = Image.Exif()
        exif[271] = "DJI"
        exif[272] = "M3T"
        exif[306] = "2025:08:25 12:16:42"
        buf = BytesIO()
        image.save(buf, "JPEG", quality=60, exif=exif)
        return buf.getvalue()
    return make((640, 512)), make((4000, 3000))


def archive(path, modality, counter_list, data, *, timestamp=None):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as zipped:
        for seq in counter_list:
            stamp = timestamp.get(seq, "20250825121642") if timestamp else "20250825121642"
            zipped.writestr(
                f"DJI_{stamp}_{seq:04d}_{modality}.JPG", data,
            )
    return path


def _sources(tmp_path, samples):
    thermal_bytes, rgb_bytes = samples
    t = archive(tmp_path / "thermal.zip", "T", [128, 129, 130], thermal_bytes)
    v = archive(tmp_path / "rgb.zip", "V", [128, 129], rgb_bytes)
    return t, v


def test_archive_audit_requires_timestamp_not_only_identical_counter(
    tmp_path, synthetic_jpegs,
):
    t, v = _sources(tmp_path, synthetic_jpegs)
    report = audit_original_m3t_archives(t, v)
    assert report.paired_sequences == ("0128", "0129")
    assert report.thermal_only_sequences == ("0130",)
    assert report.rgb_only_sequences == ()
    assert report.mismatched_timestamp_sequences == ()
    assert report.summary()["confirmed_pairs"] == 2
    assert report.summary()["thermal_without_rgb"] == 1
    assert "GpsLatitude" not in str(report.summary())
    assert "20250825" not in str(report.summary())


def test_staging_preserves_all_bytes_but_never_modifies_original_zips(
    tmp_path, synthetic_jpegs,
):
    t, v = _sources(tmp_path, synthetic_jpegs)
    originals = (sha256(t.read_bytes()).hexdigest(), sha256(v.read_bytes()).hexdigest())
    destination = tmp_path / "selected"
    done = stage_original_m3t_archives(t, v, destination)
    assert done["matched_pairs"] == 2
    assert done["staged_thermal"] == 2
    assert done["staged_rgb"] == 2
    assert done["unpaired_thermal_not_staged"] == 1
    assert len(list(destination.glob("*_T.JPG"))) == 2
    assert len(list(destination.glob("*_V.JPG"))) == 2
    assert not (destination / "DJI_20250825121642_0130_T.JPG").exists()
    ledger = json.loads((destination / "m3t-original-provenance.json").read_text())
    assert len(ledger["files"]) == 4
    assert not any(x["human_reviewed"] for x in ledger["files"])
    assert not any(x["training_rights_approved"] for x in ledger["files"])
    assert "gps" not in (destination / "m3t-original-provenance.json").read_text().lower()
    with zipfile.ZipFile(t) as src:
        for original in src.namelist()[:2]:
            assert (destination / original).read_bytes() == src.read(original)
    assert sha256(t.read_bytes()).hexdigest() == originals[0]
    assert sha256(v.read_bytes()).hexdigest() == originals[1]
    assert not (tmp_path / "solarcheck.sqlite3").exists()


def test_unpaired_thermal_stages_only_when_explicitly_requested(
    tmp_path, synthetic_jpegs,
):
    t, v = _sources(tmp_path, synthetic_jpegs)
    destination = tmp_path / "all-thermal"
    done = stage_original_m3t_archives(
        t, v, destination, include_unpaired_thermal=True,
    )
    assert done["staged_thermal"] == 3
    assert done["staged_rgb"] == 2
    assert done["unpaired_thermal_explicitly_staged"] == 1
    assert (destination / "DJI_20250825121642_0130_T.JPG").exists()
    assert done["status"] == "private_originals_not_report_or_training_approved"


def test_existing_destination_is_never_replaced(tmp_path, synthetic_jpegs):
    t, v = _sources(tmp_path, synthetic_jpegs)
    dst = tmp_path / "existing"
    dst.mkdir()
    (dst / "valuable.txt").write_text("do not delete")
    with pytest.raises(PermissionError, match="new absolute destination"):
        stage_original_m3t_archives(t, v, dst)
    assert (dst / "valuable.txt").read_text() == "do not delete"


def test_pair_counter_same_but_timestamp_conflict_fails_staging(
    tmp_path, synthetic_jpegs,
):
    thermal, rgb = synthetic_jpegs
    t = archive(tmp_path / "thermal.zip", "T", [128], thermal)
    v = archive(
        tmp_path / "rgb.zip", "V", [128], rgb,
        timestamp={128: "20250825121643"},
    )
    # No actual EXIF read needed to detect this unsafe filename conflict.
    result = audit_original_m3t_archives(t, v, inspect_images=False)
    assert result.paired_sequences == ()
    assert result.mismatched_timestamp_sequences == ("0128",)
    with pytest.raises(ValueError):
        audit_original_m3t_archives(t, v)
    with pytest.raises((ValueError, PermissionError)):
        stage_original_m3t_archives(t, v, tmp_path / "must-not-exist")
    assert not (tmp_path / "must-not-exist").exists()


def test_duplicate_counters_and_path_traversal_rejected(tmp_path, synthetic_jpegs):
    thermal, rgb = synthetic_jpegs
    t, v = _sources(tmp_path, synthetic_jpegs)
    with zipfile.ZipFile(t, "a") as zipped:
        zipped.writestr("DJI_20250825121644_0128_T.JPG", thermal)
    with pytest.raises(ValueError, match="duplicate"):
        audit_original_m3t_archives(t, v, inspect_images=False)
    t.unlink()
    with zipfile.ZipFile(t, "w") as zipped:
        zipped.writestr("../DJI_20250825121642_0128_T.JPG", thermal)
    with pytest.raises(PermissionError, match="unsafe"):
        audit_original_m3t_archives(t, v, inspect_images=False)


def test_wrong_camera_model_or_raster_never_accepted(tmp_path, synthetic_jpegs):
    t, v = _sources(tmp_path, synthetic_jpegs)
    bad = Image.new("RGB", (200, 200), (255, 0, 0))
    exif = Image.Exif()
    exif[271] = "DJI"
    exif[272] = "M3T"
    exif[306] = "2025:08:25 12:16:42"
    buf = BytesIO()
    bad.save(buf, "JPEG", exif=exif)
    t.unlink()
    archive(t, "T", [128, 129], buf.getvalue())
    with pytest.raises(ValueError, match="sensor raster"):
        audit_original_m3t_archives(t, v)


def test_rgb_only_or_partial_pair_is_never_reported_as_complete(
    tmp_path, synthetic_jpegs,
):
    thermal, rgb = synthetic_jpegs
    t = archive(tmp_path / "thermal.zip", "T", [128], thermal)
    v = archive(tmp_path / "rgb.zip", "V", [128, 129], rgb)
    audit = audit_original_m3t_archives(t, v)
    assert audit.summary()["rgb_without_thermal"] == 1
    assert not audit.summary()["all_pairs_consistent"]
    with pytest.raises(PermissionError, match="unmatched RGB"):
        stage_original_m3t_archives(t, v, tmp_path / "staged")
    assert not (tmp_path / "staged").exists()
