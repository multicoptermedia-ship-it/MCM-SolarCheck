"""Offline ZIP orchestration never returns confidential camera metadata."""
from __future__ import annotations

import json
import pytest

from mcm_solarcheck.offline.m3t_original_zips import run_local_archive_audit
from test_m3t_original_zip_archive import archive


def test_operator_audit_is_aggregate_only_and_report_exclusive(tmp_path, synthetic_jpegs=None):
    from PIL import Image
    from io import BytesIO

    def fixture(size):
        exif = Image.Exif()
        exif[271] = "DJI"
        exif[272] = "M3T"
        exif[306] = "2025:08:25 12:16:42"
        io = BytesIO()
        Image.new("RGB", size, color="blue").save(io, "JPEG", exif=exif)
        return io.getvalue()

    t = archive(tmp_path / "t.zip", "T", [128, 129], fixture((640, 512)))
    v = archive(tmp_path / "v.zip", "V", [128], fixture((4000, 3000)))
    report = tmp_path / "audit.json"
    summary = run_local_archive_audit(t, v, report_path=report)
    assert summary["confirmed_pairs"] == 1
    assert summary["thermal_without_rgb"] == 1
    text = report.read_text(encoding="utf-8")
    assert "20250825" not in text
    assert "GPS" not in text
    assert "camera_pose" not in text
    with pytest.raises(FileExistsError):
        run_local_archive_audit(t, v, report_path=report)


def test_explicit_staging_reports_all_thermal_without_assuming_rgb(tmp_path):
    from PIL import Image
    from io import BytesIO

    def fixture(size):
        exif = Image.Exif()
        exif[271] = "DJI"
        exif[272] = "M3T"
        exif[306] = "2025:08:25 12:16:42"
        output = BytesIO()
        Image.new("RGB", size, (50, 60, 80)).save(output, "JPEG", exif=exif)
        return output.getvalue()

    t = archive(tmp_path / "t.zip", "T", [128, 129], fixture((640, 512)))
    v = archive(tmp_path / "v.zip", "V", [128], fixture((4000, 3000)))
    out = tmp_path / "private"
    summary = run_local_archive_audit(
        t, v, staged_directory=out, include_unpaired_thermal=True,
    )
    assert summary["local_staging"]["staged_thermal"] == 2
    assert summary["local_staging"]["staged_rgb"] == 1
    assert summary["local_staging"]["unpaired_thermal_explicitly_staged"] == 1
    assert len(list(out.glob("*_T.JPG"))) == 2
    assert len(list(out.glob("*_V.JPG"))) == 1
    assert json.loads((out / "m3t-original-provenance.json").read_text())["status"] == (
        "private_originals_not_report_or_training_approved"
    )
