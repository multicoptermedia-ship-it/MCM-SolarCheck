"""Persisted, project-scoped expert review: queue -> decision -> SQLite audit."""
import json
from pathlib import Path

import pytest

from mcm_solarcheck.domain.models import Finding, ThermalFrame
from mcm_solarcheck.review.findings import ReviewStatus
from mcm_solarcheck.services.project_pipeline import ProjectApplicationService
from mcm_solarcheck.services.workflow import WorkflowStage
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult


def make_service(tmp_path):
    database = ProjectDatabase(tmp_path / "review.sqlite3")
    database.initialize()
    database.create_project("P1", "Solarpark 1")
    database.create_project("P2", "Solarpark 2")
    service = ProjectApplicationService(database)
    for project in ("P1", "P2"):
        frame = ThermalFrame(
            frame_id="T1", source_file=Path("T1.JPG"),
            thermal_width=640, thermal_height=512, thermal_source="raw",
        )
        quality = ThermalQualityResult(
            ThermalQualityGrade.PASS, (),
            RawThermalStatistics(1, 10, 5.0, 5.0, 9.0, 10.0, 9),
        )
        database.save_thermal_frame(project, frame, quality)
        database.save_findings(project, (
            Finding(
                "F1", "T1", 1, 2, module_id="M1",
                metadata={"source_kind": "candidate", "original": "retained"},
            ),
        ))
    return service


def audit_rows(service, project):
    with service.database.connect() as db:
        return tuple(db.execute(
            "SELECT finding_id,status,reviewer,note FROM finding_reviews "
            "WHERE project_id=? ORDER BY review_id",
            (project,),
        ).fetchall())


def test_pending_queue_is_project_scoped_and_bounded(tmp_path):
    service = make_service(tmp_path)
    first = service.pending_review_findings("P1", limit=1)
    assert len(first) == 1
    assert first[0].finding_id == "F1"
    assert first[0].reviewer_status == "unreviewed"
    assert service.pending_review_findings("P2")[0].finding_id == "F1"

    with pytest.raises(KeyError, match="Unknown project"):
        service.pending_review_findings("missing")
    with pytest.raises(ValueError, match="positive integer"):
        service.pending_review_findings("P1", limit=0)
    with pytest.raises(ValueError, match="positive integer"):
        service.pending_review_findings("P1", limit=True)


def test_explicit_expert_decision_updates_only_selected_project_and_audits(tmp_path):
    service = make_service(tmp_path)
    assert not service.state("P1").readiness(WorkflowStage.REPORT).ready

    reviewed, audit, state = service.review_pending_finding(
        "P1", "F1", status=ReviewStatus.CONFIRMED,
        reviewer="  Gutachterin  ", note="Geprüft anhand des Bildes",
    )
    assert reviewed.reviewer_status == "confirmed"
    assert reviewed.metadata["source_kind"] == "candidate"
    assert reviewed.metadata["review_source"] == "human"
    assert audit.reviewer == "Gutachterin"
    assert audit.note == "Geprüft anhand des Bildes"
    assert state.readiness(WorkflowStage.REPORT).ready
    assert service.pending_review_findings("P1") == ()
    assert len(service.pending_review_findings("P2")) == 1
    assert service.import_summary("P1").confirmed_findings == 1
    assert service.import_summary("P2").confirmed_findings == 0

    rows = audit_rows(service, "P1")
    assert len(rows) == 1
    assert tuple(rows[0]) == (
        "F1", "confirmed", "Gutachterin", "Geprüft anhand des Bildes",
    )
    with service.database.connect() as db:
        stored = db.execute(
            "SELECT reviewer_status,metadata_json FROM findings "
            "WHERE project_id=? AND finding_id=?", ("P1", "F1"),
        ).fetchone()
    assert stored["reviewer_status"] == "confirmed"
    assert json.loads(stored["metadata_json"]) == {
        "source_kind": "candidate", "original": "retained",
        "review_source": "human",
    }


@pytest.mark.parametrize("decision", [ReviewStatus.REJECTED, ReviewStatus.UNCLEAR])
def test_other_explicit_decisions_are_audited(tmp_path, decision):
    service = make_service(tmp_path)
    _reviewed, audit, _state = service.review_pending_finding(
        "P1", "F1", status=decision, reviewer="Expertin",
    )
    assert audit.status is decision
    assert len(audit_rows(service, "P1")) == 1
    assert service.import_summary("P1").unreviewed_findings == 0


def test_duplicate_and_stale_decisions_never_create_second_audit(tmp_path):
    service = make_service(tmp_path)
    _reviewed, audit, _state = service.review_pending_finding(
        "P1", "F1", status=ReviewStatus.REJECTED, reviewer="A",
    )
    with pytest.raises(ValueError, match="already been reviewed"):
        service.review_pending_finding(
            "P1", "F1", status=ReviewStatus.CONFIRMED, reviewer="B",
        )
    # A queued UI decision can outlive its original read; persistence must
    # still compare-and-set the current row inside the same transaction.
    with pytest.raises(ValueError, match="no longer unreviewed"):
        service.database.save_review(
            audit, project_id="P1", require_unreviewed=True,
        )
    assert len(audit_rows(service, "P1")) == 1
    assert service.import_summary("P1").rejected_findings == 1


def test_no_implicit_decision_and_invalid_actor_cannot_write(tmp_path):
    service = make_service(tmp_path)
    for invalid in (ReviewStatus.UNREVIEWED, "confirmed", None):
        with pytest.raises(ValueError, match="explicit completed"):
            service.review_pending_finding(
                "P1", "F1", status=invalid, reviewer="Expert",
            )
    with pytest.raises(ValueError, match="reviewer"):
        service.review_pending_finding(
            "P1", "F1", status=ReviewStatus.CONFIRMED, reviewer="  ",
        )
    with pytest.raises(KeyError, match="Unknown finding"):
        service.review_pending_finding(
            "P1", "not-found", status=ReviewStatus.CONFIRMED, reviewer="Expert",
        )
    assert len(audit_rows(service, "P1")) == 0
    assert service.import_summary("P1").unreviewed_findings == 1
    assert not service.state("P1").readiness(WorkflowStage.REPORT).ready


def test_empty_project_workflow_gate_still_rejects_review(tmp_path):
    db = ProjectDatabase(tmp_path / "empty.sqlite3")
    db.initialize()
    db.create_project("empty", "Not processed")
    service = ProjectApplicationService(db)
    with pytest.raises(ValueError, match="review action is blocked"):
        service.review_pending_finding(
            "empty", "F1", status=ReviewStatus.CONFIRMED, reviewer="Expert",
        )
