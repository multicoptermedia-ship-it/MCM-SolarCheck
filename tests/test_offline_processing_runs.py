"""Processing-run safety: v21 provenance never grants a false completion.

Synthetic SQLite frames only. No authentic DJI files and no analysis claims.
"""
from __future__ import annotations

import sqlite3

import pytest

from mcm_solarcheck.services.offline_processing_inventory import (
    capture_offline_processing_inventory,
)
from mcm_solarcheck.services.offline_processing_runs import (
    begin_offline_processing_run,
    latest_offline_processing_run,
    stop_offline_processing_run,
)
from mcm_solarcheck.storage.sqlite import ProjectDatabase, SCHEMA_VERSION


def database(tmp_path):
    db = ProjectDatabase(tmp_path / "safe.sqlite3")
    db.initialize()
    db.create_project("P1", "Example 1")
    db.create_project("P2", "Example 2")
    return db


def add_thermal(db, project_id, frame_id="T1", path="C:/PRIVATE/T1.JPG"):
    with db.connect() as sql:
        sql.execute(
            "INSERT INTO thermal_frames "
            "(project_id,frame_id,source_file,thermal_source) VALUES (?,?,?,?)",
            (project_id, frame_id, path, "raw"),
        )


def add_rgb(db, project_id, frame_id="V1", path="C:/PRIVATE/V1.JPG"):
    with db.connect() as sql:
        sql.execute(
            "INSERT INTO image_frames(project_id,frame_id,source_file) "
            "VALUES (?,?,?)", (project_id, frame_id, path),
        )


def test_inventory_is_project_scoped_and_not_fake_image_verification(tmp_path):
    db = database(tmp_path)
    with pytest.raises(KeyError, match="Unknown project"):
        capture_offline_processing_inventory(db, "missing")
    empty = capture_offline_processing_inventory(db, "P1")
    assert empty.thermal_frames == 0
    assert not empty.can_plan_processing
    assert len(empty.fingerprint) == 64
    assert "PRIVATE" not in repr(empty)

    add_thermal(db, "P1")
    one = capture_offline_processing_inventory(db, "P1")
    assert one.thermal_frames == one.expected_thermal_work == 1
    assert one.can_plan_processing
    assert one.fingerprint != empty.fingerprint
    assert one.fingerprint != capture_offline_processing_inventory(db, "P2").fingerprint

    # No image bytes are needed for this *database inventory* fingerprint.
    add_rgb(db, "P1")
    changed = capture_offline_processing_inventory(db, "P1")
    assert changed.rgb_frames == 1
    assert changed.fingerprint != one.fingerprint


def test_run_start_stop_cannot_claim_completion(tmp_path):
    db = database(tmp_path)
    with pytest.raises(ValueError, match="thermal inputs"):
        begin_offline_processing_run(db, "P1", pipeline_version="pilot-v1")
    assert latest_offline_processing_run(db, "P1") is None

    add_thermal(db, "P1")
    started = begin_offline_processing_run(
        db, "P1", pipeline_version="pilot-v1",
    )
    assert started.status == "running"
    assert started.expected_thermal_frames == 1
    assert not started.stale_inputs
    assert latest_offline_processing_run(db, "P2") is None

    with pytest.raises(ValueError, match="already active"):
        begin_offline_processing_run(db, "P1", pipeline_version="pilot-v1")
    with pytest.raises(ValueError, match="permitted"):
        stop_offline_processing_run(
            db, "P1", started.run_id, outcome="completed",
        )
    with pytest.raises(ValueError, match="not found"):
        stop_offline_processing_run(
            db, "P2", started.run_id, outcome="cancelled",
        )
    with pytest.raises(ValueError, match="exceed"):
        stop_offline_processing_run(
            db, "P1", started.run_id, outcome="failed",
            processed_thermal_frames=2,
        )
    stop_offline_processing_run(
        db, "P1", started.run_id, outcome="cancelled",
        processed_thermal_frames=1,
    )
    assert latest_offline_processing_run(db, "P1").status == "cancelled"
    with pytest.raises(ValueError, match="not found"):
        stop_offline_processing_run(
            db, "P1", started.run_id, outcome="failed",
        )
    new = begin_offline_processing_run(db, "P1", pipeline_version="pilot-v2")
    assert new.run_id != started.run_id
    stop_offline_processing_run(
        db, "P1", new.run_id, outcome="failed",
        failed_thermal_frames=1,
    )
    assert latest_offline_processing_run(db, "P1").status == "failed"
    with db.connect() as sql:
        states = [row[0] for row in sql.execute(
            "SELECT status FROM offline_processing_runs WHERE project_id=?",
            ("P1",),
        )]
    assert sorted(states) == ["cancelled", "failed"]


def test_new_import_invalidates_old_run_and_preserves_original_records(tmp_path):
    db = database(tmp_path)
    add_thermal(db, "P1")
    started = begin_offline_processing_run(
        db, "P1", pipeline_version="test-v1",
    )
    stop_offline_processing_run(db, "P1", started.run_id, outcome="failed")
    before = latest_offline_processing_run(db, "P1")
    assert not before.stale_inputs
    add_rgb(db, "P1")
    after = latest_offline_processing_run(db, "P1")
    assert after.stale_inputs
    assert after.run_id == before.run_id
    assert after.input_fingerprint == before.input_fingerprint
    assert after.status == "failed"
    assert capture_offline_processing_inventory(db, "P1").image_pairs == 0


def test_schema_20_upgrade_adds_empty_ledger_without_backfill(tmp_path):
    db = database(tmp_path)
    add_thermal(db, "P1")
    with db.connect() as sql:
        sql.execute("DROP TABLE offline_processing_runs")
        sql.execute("UPDATE schema_info SET version=20")
    db.initialize()
    with db.connect() as sql:
        assert sql.execute("SELECT version FROM schema_info").fetchone()[0] == SCHEMA_VERSION
        assert sql.execute(
            "SELECT COUNT(*) FROM offline_processing_runs",
        ).fetchone()[0] == 0
    assert latest_offline_processing_run(db, "P1") is None
