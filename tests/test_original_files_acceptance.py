"""Read-only acceptance for real-file workflow, with synthetic DJI fixtures only."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3

import pytest

from mcm_solarcheck.importers.m3t_original_files_audit import audit_original_m3t_files
from mcm_solarcheck.importers.m3t_original_files_staging import stage_original_m3t_files
from mcm_solarcheck.offline.original_files_acceptance import verify_original_file_project
from mcm_solarcheck.offline.original_files_acceptance_cli import (
    evaluate, main, select_original_files,
)
from test_original_files_project_bridge import loose_originals


def build_project(tmp_path, selected, *, pairs=1):
    database = tmp_path / "pilot.sqlite3"
    target = tmp_path / "private-m3t-originals" / "batch001"
    target.parent.mkdir()
    stage_original_m3t_files(selected, target)
    with sqlite3.connect(database) as db:
        db.executescript("""
        CREATE TABLE projects(project_id TEXT PRIMARY KEY);
        CREATE TABLE image_frames(project_id TEXT, source_file TEXT);
        CREATE TABLE thermal_frames(project_id TEXT, source_file TEXT);
        CREATE TABLE image_pairs(project_id TEXT);
        INSERT INTO projects(project_id) VALUES ('PV-PILOT');
        """)
        for item in selected:
            table = "thermal_frames" if item.name.endswith("_T.JPG") else "image_frames"
            db.execute(f"INSERT INTO {table} VALUES (?,?)", ("PV-PILOT", str(target / item.name)))
        for _ in range(pairs):
            db.execute("INSERT INTO image_pairs VALUES ('PV-PILOT')")
    return database, target


def report(selected, **kw):
    return evaluate(selected, expected_thermal=2, expected_rgb=1,
                    expected_metadata_pairs=1, **kw)


def test_preflight_read_only_with_unpaired_thermal(tmp_path):
    selected = loose_originals(tmp_path)
    audit = audit_original_m3t_files(selected)
    assert (audit.thermal_images, audit.rgb_images,
            audit.matched_pairs, audit.thermal_only, audit.rgb_only) == (2, 1, 1, 1, 0)
    before = tuple(path.read_bytes() for path in selected)
    summary = report(selected)
    assert summary["local_originals_inspected"] == 3
    assert summary["stage"] == "pre_import_original_file_audit"
    assert "20250825" not in json.dumps(summary)
    assert "DJI_" not in json.dumps(summary)
    assert tuple(path.read_bytes() for path in selected) == before
    assert not (tmp_path / "private-m3t-originals").exists()


def test_postcheck_verifies_project_copy_byte_integrity_without_writes(tmp_path):
    originals = loose_originals(tmp_path)
    database, folder = build_project(tmp_path, originals)
    before = database.read_bytes()
    checked = report(originals, database=database, project_id="PV-PILOT")
    assert checked["persistent_thermal_images"] == 2
    assert checked["persistent_rgb_images"] == 1
    assert checked["persistent_analysis_pair_records"] == 1
    assert checked["verified_original_copies"] == 3
    assert checked["source_copies_and_provenance_sha256_agree"] is True
    assert checked["analysis_pair_review_required"] is False
    assert checked["radiometric_celsius_validated"] is False
    assert database.read_bytes() == before
    assert len(list(folder.glob("*_T.JPG"))) == 2


def test_missing_analysis_pair_is_review_flag_not_fake_success(tmp_path):
    selected = loose_originals(tmp_path)
    database, _ = build_project(tmp_path, selected, pairs=0)
    checked = report(selected, database=database, project_id="PV-PILOT")
    assert checked["filename_timestamp_matched_pairs"] == 1
    assert checked["persistent_analysis_pair_records"] == 0
    assert checked["analysis_pair_review_required"] is True


def test_mutated_saved_or_source_image_is_detected(tmp_path):
    selected = loose_originals(tmp_path)
    db, saved = build_project(tmp_path, selected)
    copied = saved / selected[0].name
    copied.write_bytes(b"modified")
    with pytest.raises(ValueError):
        report(selected, database=db, project_id="PV-PILOT")
    copied.write_bytes(selected[0].read_bytes())
    selected[0].write_bytes(b"modified source")
    with pytest.raises((OSError, ValueError)):
        report(selected, database=db, project_id="PV-PILOT")


def test_bad_manifest_unknown_project_and_missing_db_fail_closed(tmp_path):
    selected = loose_originals(tmp_path)
    database, saved = build_project(tmp_path, selected)
    with pytest.raises(KeyError):
        report(selected, database=database, project_id="UNRELATED")
    missing = tmp_path / "missing.sqlite3"
    with pytest.raises(PermissionError):
        report(selected, database=missing, project_id="PV-PILOT")
    assert not missing.exists()
    manifest = saved / "m3t-original-provenance.json"
    obj = json.loads(manifest.read_text())
    obj["files"][0]["training_rights_approved"] = True
    manifest.write_text(json.dumps(obj), encoding="utf-8")
    with pytest.raises(ValueError):
        report(selected, database=database, project_id="PV-PILOT")


def test_source_folders_can_be_separate_and_not_zip(tmp_path):
    selected = loose_originals(tmp_path)
    thermal_dir = selected[0].parent
    rgb_dir = tmp_path / "only-rgb"
    rgb_dir.mkdir()
    rgb = rgb_dir / selected[2].name
    selected[2].rename(rgb)
    chosen = select_original_files((thermal_dir, rgb_dir), ())
    assert {p.name for p in chosen} == {p.name for p in selected}
    assert report(chosen)["filename_timestamp_matched_pairs"] == 1
    with pytest.raises(ValueError):
        evaluate(chosen, expected_thermal=999, expected_rgb=1, expected_metadata_pairs=1)


def test_noncanonical_jpg_cannot_be_silently_skipped_by_importer(tmp_path):
    selected = loose_originals(tmp_path)
    bad = selected[0].with_suffix(".jpg")
    selected[0].rename(bad)
    with pytest.raises(ValueError, match="canonical"):
        audit_original_m3t_files((bad, selected[1], selected[2]))


def test_cli_redacts_error_message_and_confidential_paths(monkeypatch, capsys):
    def bad(*args, **kwargs):
        raise ValueError("PRIVATE EXIF GPS CUSTOMER SOURCE D:\\SECRET")
    monkeypatch.setattr("mcm_solarcheck.offline.original_files_acceptance_cli.evaluate", bad)
    rc = main(["--source-folder", "C:/private/dji"])
    stdout = capsys.readouterr().out
    assert rc == 2
    assert '"accepted": false' in stdout
    assert "SECRET" not in stdout
    assert "C:/private" not in stdout
