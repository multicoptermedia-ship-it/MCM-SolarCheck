"""Shipped offline desktop MUST NOT review staged candidates before full processing.

Only synthetic SQLite fixtures; no DJI originals and no automatic approvals.
Legacy human decisions remain on disk even if later access is fail-closed.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mcm_solarcheck.offline.composition import build_offline_services
from mcm_solarcheck.review.findings import ReviewStatus
from mcm_solarcheck.services.offline_processing_runs import (
    begin_offline_processing_run,
    stop_offline_processing_run,
)
from mcm_solarcheck.services.workflow import WorkflowAction, WorkflowStage


def seed(tmp_path):
    service = build_offline_services(tmp_path / "isolated.sqlite3").projects
    for project in ("P1", "P2"):
        service.create_project(project, "Synthetic")
        with service.database.connect() as sql:
            sql.execute(
                "INSERT INTO thermal_frames "
                "(project_id,frame_id,source_file,thermal_source) "
                "VALUES (?,?,?,?)", (project, "T1", "synthetic.jpg", "raw"),
            )
            sql.execute(
                "INSERT INTO findings "
                "(project_id,finding_id,thermal_frame_id,pixel_x,pixel_y,"
                "finding_type,reviewer_status) VALUES (?,?,?,?,?,?,?)",
                (project, "F1", "T1", 1, 2, "raw_unverified", "unreviewed"),
            )
    return service


def test_offline_staged_candidates_never_grant_review_report_or_export(tmp_path):
    service = seed(tmp_path)
    for project in ("P1", "P2"):
        state = service.state(project)
        for stage in (WorkflowStage.REVIEW, WorkflowStage.REPORT, WorkflowStage.EXPORT):
            assert not state.readiness(stage).ready
            assert "Vollständiger Verarbeitungslauf noch nicht nachgewiesen" in (
                state.readiness(stage).blockers
            )
        for action in (
            WorkflowAction.REVIEW,
            WorkflowAction.PREPARE_REPORT,
            WorkflowAction.EXPORT,
        ):
            with pytest.raises(ValueError, match="action is blocked"):
                service.require(project, action)
        assert service.pending_review_findings(project)[0].finding_id == "F1"

    with pytest.raises(ValueError, match="review action is blocked"):
        service.review_pending_finding(
            "P1", "F1", status=ReviewStatus.CONFIRMED,
            reviewer="Test reviewer",
        )
    from mcm_solarcheck.domain.models import Finding
    with pytest.raises(ValueError, match="review action is blocked"):
        service.review_finding(
            "P1", Finding("F1", "T1", 1, 2),
            status=ReviewStatus.CONFIRMED, reviewer="Test reviewer",
            reviewed_at_utc=datetime(2026, 10, 24, tzinfo=timezone.utc),
        )
    assert service.import_summary("P1").unreviewed_findings == 1
    with service.database.connect() as sql:
        assert sql.execute("SELECT COUNT(*) FROM finding_reviews").fetchone()[0] == 0


@pytest.mark.parametrize("outcome", ("running", "failed", "cancelled"))
def test_offline_run_without_success_cannot_unlock_review(tmp_path, outcome):
    service = seed(tmp_path)
    run = begin_offline_processing_run(
        service.database, "P1", pipeline_version="untrusted-synthetic",
    )
    if outcome != "running":
        stop_offline_processing_run(
            service.database, "P1", run.run_id, outcome=outcome,
        )
    assert not service.state("P1").readiness(WorkflowStage.REVIEW).ready
    assert not service.state("P1").readiness(WorkflowStage.REPORT).ready
    assert not service.state("P1").readiness(WorkflowStage.EXPORT).ready
    assert not service.state("P2").readiness(WorkflowStage.REVIEW).ready


def test_forged_completed_marker_is_not_worker_proof(tmp_path):
    service = seed(tmp_path)
    run = begin_offline_processing_run(
        service.database, "P1", pipeline_version="untrusted-synthetic",
    )
    with service.database.connect() as sql:
        sql.execute(
            "UPDATE offline_processing_runs SET status='completed',"
            "processed_thermal_frames=expected_thermal_frames,"
            "failed_thermal_frames=0,finished_at=CURRENT_TIMESTAMP "
            "WHERE project_id='P1' AND run_id=?",
            (run.run_id,),
        )
    blocked = service.state("P1").readiness(WorkflowStage.REVIEW)
    assert blocked.ready is False
    assert "Abschluss des vollständigen Verarbeitungslaufs nicht verifiziert" in blocked.blockers
    with pytest.raises(ValueError, match="review action is blocked"):
        service.review_pending_finding(
            "P1", "F1", status=ReviewStatus.REJECTED, reviewer="Expert",
        )


def test_changed_inputs_cannot_restore_review_and_old_audits_are_preserved(tmp_path):
    service = seed(tmp_path)
    # Existing legacy audited decisions must never be silently erased.
    with service.database.connect() as sql:
        sql.execute(
            "UPDATE findings SET reviewer_status='confirmed' "
            "WHERE project_id='P2' AND finding_id='F1'"
        )
        sql.execute(
            "INSERT INTO finding_reviews "
            "(project_id,finding_id,status,reviewer,reviewed_at_utc) "
            "VALUES (?,?,?,?,?)",
            ("P2", "F1", "confirmed", "Human before migration",
             "2026-10-01T10:00:00+00:00"),
        )
    started = begin_offline_processing_run(
        service.database, "P1", pipeline_version="untrusted-synthetic",
    )
    stop_offline_processing_run(
        service.database, "P1", started.run_id, outcome="failed",
    )
    with service.database.connect() as sql:
        sql.execute(
            "INSERT INTO image_frames(project_id,frame_id,source_file) "
            "VALUES (?,?,?)", ("P1", "R2", "unreadable-unverified.jpg"),
        )
    assert "Bilddaten seit dem letzten Verarbeitungslauf geändert" in (
        service.state("P1").readiness(WorkflowStage.REVIEW).blockers
    )
    with service.database.connect() as sql:
        row = sql.execute(
            "SELECT status,reviewer FROM finding_reviews "
            "WHERE project_id='P2'"
        ).fetchone()
    assert tuple(row) == ("confirmed", "Human before migration")
    assert not service.state("P2").readiness(WorkflowStage.EXPORT).ready


def test_successful_read_only_file_preflight_still_cannot_unlock_review(tmp_path):
    """Even 100%-matching imported bytes are not a full PV analysis."""
    from hashlib import sha256
    from PIL import Image

    from mcm_solarcheck.services.offline_imported_image_check import (
        check_imported_image_originals,
    )

    service = build_offline_services(tmp_path / "preflight.sqlite3").projects
    service.create_project("P1", "Synthetic")
    image = tmp_path / "test-thermal.jpg"
    Image.new("RGB", (32, 32), (100, 20, 30)).save(image)
    with service.database.connect() as sql:
        sql.execute(
            "INSERT INTO thermal_frames "
            "(project_id,frame_id,source_file,thermal_source) "
            "VALUES (?,?,?,?)", ("P1", "T1", str(image), "raw"),
        )
        sql.execute(
            "INSERT INTO training_samples "
            "(sample_id,project_id,source_frame_id,source_file,modality,"
            "content_sha256,label_status,rights_status) VALUES (?,?,?,?,?,?,?,?)",
            ("S1", "P1", "T1", str(image), "thermal",
             sha256(image.read_bytes()).hexdigest(), "unlabeled", "unverified"),
        )
        sql.execute(
            "INSERT INTO findings "
            "(project_id,finding_id,thermal_frame_id,pixel_x,pixel_y,"
            "finding_type,reviewer_status) VALUES (?,?,?,?,?,?,?)",
            ("P1", "F1", "T1", 1, 2, "raw_candidate", "unreviewed"),
        )
    preflight = check_imported_image_originals(service.database, "P1")
    assert preflight.safe_to_process
    assert preflight.valid_images == preflight.checksum_verified == 1
    assert not service.state("P1").readiness(WorkflowStage.REVIEW).ready
    assert not service.state("P1").readiness(WorkflowStage.REPORT).ready
    assert not service.state("P1").readiness(WorkflowStage.EXPORT).ready
