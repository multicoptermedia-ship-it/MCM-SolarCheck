"""No module detections or fake review permissions from RGB readiness."""
from __future__ import annotations

from mcm_solarcheck.offline.composition import build_offline_services
from mcm_solarcheck.services.offline_module_detection_readiness import (
    assess_module_detection_readiness,
)
from mcm_solarcheck.services.workflow import WorkflowStage


def test_rgb_geometry_and_recorded_hash_never_claim_modules(tmp_path):
    svc = build_offline_services(tmp_path / "project.sqlite3").projects
    svc.create_project("P1", "RGB project")
    svc.create_project("P2", "Other project")
    with svc.database.connect() as db:
        db.execute(
            "INSERT INTO image_frames(project_id,frame_id,source_file,width,height) "
            "VALUES ('P1','R1','synthetic.JPG',4000,3000)"
        )
        db.execute(
            "INSERT INTO training_samples "
            "(sample_id,project_id,source_frame_id,source_file,modality,"
            "content_sha256,label_status,rights_status) "
            "VALUES (?,?,?,?,?,?,?,?)",
            ("S1", "P1", "R1", "synthetic.JPG", "rgb", "a" * 64,
             "pending", "private"),
        )
    result = assess_module_detection_readiness(svc.database, "P1")
    assert result.rgb_frames == result.geometrically_plausible_rgb == 1
    assert result.imported_rgb_with_digest == result.rgb_ready_as_detector_inputs == 1
    assert result.no_verified_detector
    assert not result.can_run_full_module_analysis
    assert result.metadata_pairs == 0
    assert not result.changed_inputs
    assert result.read_only
    assert assess_module_detection_readiness(svc.database, "P2").rgb_frames == 0
    assert not svc.state("P1").readiness(WorkflowStage.REVIEW).ready
    with svc.database.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM pv_modules").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM offline_processing_runs").fetchone()[0] == 0


def test_missing_geometry_and_digest_are_counted_independently(tmp_path):
    svc = build_offline_services(tmp_path / "isolated.sqlite3").projects
    svc.create_project("P1", "Test")
    with svc.database.connect() as db:
        for frame, width, height in (
            ("R1", None, None), ("R2", 500, 250),
            ("R3", 0, 0), ("R4", 100_000, 100_000),
        ):
            db.execute(
                "INSERT INTO image_frames(project_id,frame_id,source_file,width,height)"
                " VALUES (?,?,?,?,?)", ("P1", frame, "unused.JPG", width, height),
            )
        db.execute(
            "INSERT INTO training_samples "
            "(sample_id,project_id,source_frame_id,source_file,modality,"
            "content_sha256,label_status,rights_status) "
            "VALUES (?,?,?,?,?,?,?,?)",
            ("S2", "P1", "R2", "unused.JPG", "rgb",
             "f" * 64, "pending", "private"),
        )
    result = assess_module_detection_readiness(svc.database, "P1")
    assert result.rgb_frames == 4
    assert result.geometrically_plausible_rgb == 1
    assert result.imported_rgb_with_digest == 1
    assert result.rgb_ready_as_detector_inputs == 1
    assert result.rgb_missing_geometry == 3
    assert result.rgb_missing_import_digest == 3
    assert not result.can_run_full_module_analysis
