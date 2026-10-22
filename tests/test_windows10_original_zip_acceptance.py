"""Synthetic acceptance of private M3T originals without customer files."""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sqlite3
from zipfile import ZipFile

import pytest
from PIL import Image

from mcm_solarcheck.offline.zip_acceptance_cli import evaluate, main


STAMP = "20250825121642"


def _jpeg(size) -> bytes:
    exif = Image.Exif()
    exif[271] = "DJI"
    exif[272] = "M3T"
    exif[306] = "2025:08:25 12:16:42"
    output = BytesIO()
    Image.new("RGB", size, (40, 60, 80)).save(output, "JPEG", exif=exif)
    return output.getvalue()


def _archives(root: Path) -> tuple[Path, Path, dict[str, bytes]]:
    thermal = root / "thermal.zip"
    rgb = root / "rgb.zip"
    originals = {
        f"DJI_{STAMP}_0128_T.JPG": _jpeg((640, 512)),
        f"DJI_{STAMP}_0129_T.JPG": _jpeg((640, 512)),
        f"DJI_{STAMP}_0128_V.JPG": _jpeg((4000, 3000)),
    }
    with ZipFile(thermal, "w") as z:
        for name, blob in originals.items():
            if name.endswith("_T.JPG"):
                z.writestr(name, blob)
    with ZipFile(rgb, "w") as z:
        for name, blob in originals.items():
            if name.endswith("_V.JPG"):
                z.writestr(name, blob)
    return thermal, rgb, originals


def _persisted(root: Path, originals: dict[str, bytes], *, include_extra=False, pairs=1):
    database = root / "project.sqlite3"
    original_folder = root / "private-m3t-originals" / "test-only"
    original_folder.mkdir(parents=True)
    with sqlite3.connect(database) as conn:
        conn.executescript("""
        CREATE TABLE projects(project_id TEXT PRIMARY KEY);
        CREATE TABLE image_frames(project_id TEXT, source_file TEXT);
        CREATE TABLE thermal_frames(project_id TEXT, source_file TEXT);
        CREATE TABLE image_pairs(project_id TEXT);
        INSERT INTO projects(project_id) VALUES ('PV-TEST');
        """)
        for _ in range(pairs):
            conn.execute("INSERT INTO image_pairs VALUES ('PV-TEST')")
        manifest = {
            "schema": 1,
            "status": "private_originals_not_report_or_training_approved",
            "staged_thermal": 2 if include_extra else 1,
            "staged_rgb": 1,
            "matched_pairs": 1,
            "files": [],
        }
        for name, blob in originals.items():
            if "_0129_T." in name and not include_extra:
                continue
            source = original_folder / name
            source.write_bytes(blob)
            kind = "T" if name.endswith("_T.JPG") else "V"
            table = "thermal_frames" if kind == "T" else "image_frames"
            conn.execute(f"INSERT INTO {table} VALUES (?,?)", ("PV-TEST", str(source)))
            manifest["files"].append({
                "filename": name, "bytes": len(blob), "sha256": sha256(blob).hexdigest(),
                "modality": kind, "human_reviewed": False,
                "training_rights_approved": False,
            })
    (original_folder / "m3t-original-provenance.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return database, original_folder


def _evaluate(t, v, **kw):
    return evaluate(t, v, expected_thermal=2, expected_rgb=1,
                    expected_metadata_pairs=1, **kw)


def test_read_only_preflight_has_aggregate_counts_only(tmp_path):
    t, v, _ = _archives(tmp_path)
    report = _evaluate(t, v)
    assert report["stage"] == "pre_import_archive_audit"
    assert report["thermal_without_rgb"] == 1
    assert report["filename_timestamp_matched_pairs"] == 1
    assert "20250825" not in json.dumps(report)
    assert not (tmp_path / "private-m3t-originals").exists()


def test_post_import_checks_durable_bytes_and_preserves_sqlite(tmp_path):
    t, v, originals = _archives(tmp_path)
    database, folder = _persisted(tmp_path, originals)
    previous = database.read_bytes()
    report = _evaluate(t, v, database=database, project_id="PV-TEST")
    assert report["stage"] == "post_import_read_only_verification"
    assert report["verified_original_copies"] == 2
    assert report["persistent_thermal_images"] == 1
    assert report["persistent_rgb_images"] == 1
    assert report["archive_and_provenance_sha256_agree"] is True
    assert report["analysis_pair_review_required"] is False
    assert database.read_bytes() == previous
    assert len(list(folder.glob("*_T.JPG"))) == 1


def test_explicit_extra_thermal_and_missing_analysis_pair_are_not_hidden(tmp_path):
    t, v, originals = _archives(tmp_path)
    database, _ = _persisted(tmp_path, originals, include_extra=True, pairs=0)
    report = _evaluate(t, v, database=database, project_id="PV-TEST",
                       include_unpaired_thermal=True)
    assert report["verified_original_copies"] == 3
    assert report["persistent_thermal_images"] == 2
    assert report["persistent_analysis_pair_records"] == 0
    assert report["analysis_pair_review_required"] is True


def test_wrong_include_choice_or_changed_copy_fails_closed(tmp_path):
    t, v, originals = _archives(tmp_path)
    database, folder = _persisted(tmp_path, originals)
    with pytest.raises(ValueError):
        _evaluate(t, v, database=database, project_id="PV-TEST",
                  include_unpaired_thermal=True)
    next(folder.glob("*_V.JPG")).write_bytes(b"tampered")
    with pytest.raises(ValueError):
        _evaluate(t, v, database=database, project_id="PV-TEST")


def test_read_only_database_missing_or_unknown_project_is_refused(tmp_path):
    t, v, originals = _archives(tmp_path)
    database, _ = _persisted(tmp_path, originals)
    with pytest.raises(KeyError):
        _evaluate(t, v, database=database, project_id="unknown")
    missing = tmp_path / "not-a-database.sqlite3"
    with pytest.raises(PermissionError):
        _evaluate(t, v, database=missing, project_id="PV-TEST")
    assert not missing.exists()


def test_cli_fails_privately_without_paths_or_exception_text(monkeypatch, capsys):
    def unexpected(*args, **kwargs):
        raise ValueError("PRIVATE CUSTOMER LOCATION AND FILE")
    monkeypatch.setattr("mcm_solarcheck.offline.zip_acceptance_cli.evaluate", unexpected)
    rc = main(["--thermal-zip", "/private/thermal.zip",
               "--rgb-zip", "/private/rgb.zip"])
    output = capsys.readouterr().out
    assert rc == 2
    assert '"accepted": false' in output
    assert "/private/" not in output
    assert "CUSTOMER" not in output
