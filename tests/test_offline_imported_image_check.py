"""Read-only imported-original preflight with synthetic JPEGs only.

No DJI content, no inferred diagnostics, no report or expert approval.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest
from PIL import Image

from mcm_solarcheck.services.offline_imported_image_check import (
    ImportedImageCheckCancelled, check_imported_image_originals,
)
from mcm_solarcheck.storage.sqlite import ProjectDatabase


def seed(tmp_path):
    db = ProjectDatabase(tmp_path / "test.sqlite3")
    db.initialize()
    db.create_project("P1", "Synthetic")
    db.create_project("P2", "Other")
    source = tmp_path / "one.jpg"
    Image.new("RGB", (32, 32), (0, 128, 1)).save(source)
    other = tmp_path / "two.jpg"
    Image.new("RGB", (48, 35), (100, 18, 31)).save(other)
    with db.connect() as sql:
        sql.execute(
            "INSERT INTO thermal_frames "
            "(project_id,frame_id,source_file,thermal_source) VALUES (?,?,?,?)",
            ("P1", "T1", str(source), "palette"),
        )
        sql.execute(
            "INSERT INTO image_frames "
            "(project_id,frame_id,source_file) VALUES (?,?,?)",
            ("P1", "V1", str(other)),
        )
        sql.execute(
            "INSERT INTO training_samples "
            "(sample_id,project_id,source_frame_id,source_file,modality,"
            "content_sha256,label_status,rights_status) "
            "VALUES (?,?,?,?,?,?,?,?)",
            ("S1", "P1", "T1", str(source), "thermal",
             sha256(source.read_bytes()).hexdigest(), "pending", "private"),
        )
    return db, source, other


def test_synthetic_imported_files_are_read_only_and_missing_hash_is_not_approved(tmp_path):
    db, thermal, rgb = seed(tmp_path)
    originals = (thermal.read_bytes(), rgb.read_bytes())
    events = []
    result = check_imported_image_originals(
        db, "P1", on_progress=lambda done, total, issues: events.append(
            (done, total, issues)
        ),
    )
    assert result.total == 2
    assert result.checked == result.valid_images == 2
    assert result.checksum_verified == 1
    assert result.without_checksum == 1
    assert result.issues == 0
    assert not result.changed_inputs
    assert result.read_only
    assert not result.safe_to_process
    assert events == [(1, 2, 0), (2, 2, 0)]
    assert (thermal.read_bytes(), rgb.read_bytes()) == originals
    with db.connect() as sql:
        assert sql.execute(
            "SELECT COUNT(*) FROM finding_reviews"
        ).fetchone()[0] == 0
        assert sql.execute(
            "SELECT COUNT(*) FROM offline_processing_runs"
        ).fetchone()[0] == 0
    other_project = check_imported_image_originals(db, "P2")
    assert other_project.total == 0 and not other_project.safe_to_process


def test_all_hashes_agree_does_not_claim_full_image_analysis(tmp_path):
    db, _, rgb = seed(tmp_path)
    with db.connect() as sql:
        sql.execute(
            "INSERT INTO training_samples "
            "(sample_id,project_id,source_frame_id,source_file,modality,"
            "content_sha256,label_status,rights_status) "
            "VALUES (?,?,?,?,?,?,?,?)",
            ("S2", "P1", "V1", str(rgb), "rgb",
             sha256(rgb.read_bytes()).hexdigest(), "pending", "private"),
        )
    result = check_imported_image_originals(db, "P1")
    assert result.safe_to_process
    # This is only local byte/structure readiness, NOT processing completion.
    with db.connect() as sql:
        assert sql.execute(
            "SELECT COUNT(*) FROM offline_processing_runs"
        ).fetchone()[0] == 0


def test_corrupt_source_and_wrong_checksum_fail_closed(tmp_path):
    db, source, rgb = seed(tmp_path)
    source.write_bytes(b"not a JPEG")
    with db.connect() as sql:
        sql.execute(
            "UPDATE training_samples SET content_sha256=? WHERE project_id='P1'",
            ("0" * 64,),
        )
    outcome = check_imported_image_originals(db, "P1")
    assert outcome.issues == 1 and outcome.valid_images == 1
    assert not outcome.safe_to_process
    rgb.unlink()
    outcome2 = check_imported_image_originals(db, "P1")
    assert outcome2.issues == 2 and outcome2.valid_images == 0
    assert not outcome2.safe_to_process


def test_cancel_during_loop_returns_no_approved_result(tmp_path):
    db, source, other = seed(tmp_path)
    state = {"cancel": False}
    with pytest.raises(ImportedImageCheckCancelled):
        check_imported_image_originals(
            db, "P1",
            should_cancel=lambda: state["cancel"],
            on_progress=lambda *_: state.__setitem__("cancel", True),
        )
    assert source.is_file() and other.is_file()


def test_change_to_project_input_during_scan_marks_report_stale(tmp_path):
    db, source, _ = seed(tmp_path)
    def change_inventory(done, total, issues):
        if done == 1:
            with db.connect() as sql:
                sql.execute(
                    "INSERT INTO image_frames(project_id,frame_id,source_file) "
                    "VALUES (?,?,?)", ("P1", "V2", str(source)),
                )
    result = check_imported_image_originals(
        db, "P1", on_progress=change_inventory,
    )
    assert result.changed_inputs
    assert not result.safe_to_process


def test_invalid_bounds_and_unknown_project(tmp_path):
    db, *_ = seed(tmp_path)
    with pytest.raises(ValueError, match="byte bound"):
        check_imported_image_originals(db, "P1", maximum_bytes=0)
    with pytest.raises(KeyError, match="Unknown project"):
        check_imported_image_originals(db, "none")


def test_dji_mpo_pillow_format_is_accepted_with_verified_source_hash(
    tmp_path, monkeypatch,
):
    """Regression: Pillow reports real DJI M3T JPG files as format 'MPO'.

    These JPEGs are synthetic; override only Pillow's reported format to
    reproduce the field observation without distributing DJI originals.
    """
    db, thermal, rgb = seed(tmp_path)
    with db.connect() as sql:
        sql.execute(
            "INSERT INTO training_samples "
            "(sample_id,project_id,source_frame_id,source_file,modality,"
            "content_sha256,label_status,rights_status) "
            "VALUES (?,?,?,?,?,?,?,?)",
            ("S2", "P1", "V1", str(rgb), "rgb",
             sha256(rgb.read_bytes()).hexdigest(), "pending", "private"),
        )

    original_open = Image.open
    def pillow_opens_as_mpo(path):
        image = original_open(path)
        image.format = "MPO"
        return image
    monkeypatch.setattr(
        "mcm_solarcheck.services.offline_imported_image_check.Image.open",
        pillow_opens_as_mpo,
    )
    source_bytes = (thermal.read_bytes(), rgb.read_bytes())
    checked = check_imported_image_originals(db, "P1")

    assert checked.total == checked.checked == checked.valid_images == 2
    assert checked.checksum_verified == 2
    assert checked.without_checksum == checked.issues == 0
    assert checked.safe_to_process
    assert (thermal.read_bytes(), rgb.read_bytes()) == source_bytes
    with db.connect() as sql:
        assert sql.execute(
            "SELECT COUNT(*) FROM offline_processing_runs"
        ).fetchone()[0] == 0
        assert sql.execute("SELECT COUNT(*) FROM finding_reviews").fetchone()[0] == 0


def test_mpo_identifier_never_bypasses_mismatched_import_checksum(
    tmp_path, monkeypatch,
):
    db, thermal, rgb = seed(tmp_path)
    original_open = Image.open
    def pillow_opens_as_mpo(path):
        image = original_open(path)
        image.format = "MPO"
        return image
    monkeypatch.setattr(
        "mcm_solarcheck.services.offline_imported_image_check.Image.open",
        pillow_opens_as_mpo,
    )
    with db.connect() as sql:
        sql.execute(
            "UPDATE training_samples SET content_sha256=? "
            "WHERE project_id='P1' AND modality='thermal'",
            ("0" * 64,),
        )
    checked = check_imported_image_originals(db, "P1")
    assert checked.valid_images == 1
    assert checked.issues == 1
    assert checked.checksum_verified == 0
    assert not checked.safe_to_process
