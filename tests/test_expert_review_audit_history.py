"""Project-bound history of real human-review audits, not computed status labels."""
from pathlib import Path

import pytest

from mcm_solarcheck.domain.models import Finding, ThermalFrame
from mcm_solarcheck.review.findings import ReviewStatus
from mcm_solarcheck.services.project_pipeline import ProjectApplicationService
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult


def make_service(tmp_path, count=54):
    db = ProjectDatabase(tmp_path / "audit.sqlite3")
    db.initialize()
    service = ProjectApplicationService(db)
    for project in ("P1", "P2"):
        service.create_project(project, "Private sample")
        db.save_thermal_frame(
            project,
            ThermalFrame(
                frame_id="T1", source_file=Path("not-a-real-flight.JPG"),
                thermal_width=640, thermal_height=512, thermal_source="raw",
            ),
            ThermalQualityResult(
                ThermalQualityGrade.PASS, (),
                RawThermalStatistics(1, 10, 5.0, 5.0, 9.0, 10.0, 9),
            ),
        )
        db.save_findings(project, tuple(
            Finding(
                f"F{i:03}", "T1", i, i + 3,
                module_id="M1", reviewer_status="unreviewed",
            ) for i in range(1, count + 1)
        ))
    return service


def test_review_history_reads_persisted_audits_in_event_order_and_pages(tmp_path):
    service = make_service(tmp_path)
    decisions = (ReviewStatus.CONFIRMED, ReviewStatus.REJECTED, ReviewStatus.UNCLEAR)
    for i in range(1, 54):
        service.review_pending_finding(
            "P1", f"F{i:03}", status=decisions[i % 3],
            reviewer="Prüferin", note=f"Kontrolle {i}",
        )
    service.review_pending_finding(
        "P2", "F001", status=ReviewStatus.CONFIRMED,
        reviewer="Anderer Prüfer", note="Isoliertes Projekt",
    )
    pages = [
        service.expert_review_history("P1", limit=25, offset=offset)
        for offset in (0, 25, 50)
    ]
    assert [(p.total, p.offset, len(p.entries)) for p in pages] == [
        (53, 0, 25), (53, 25, 25), (53, 50, 3),
    ]
    records = [a for p in pages for a in p.entries]
    assert [r.finding_id for r in records] == [
        f"F{i:03}" for i in range(53, 0, -1)
    ]
    assert len({r.review_id for r in records}) == 53
    assert all(
        r.thermal_frame_id == "T1" and r.module_id == "M1"
        for r in records
    )
    assert records[0].status == decisions[53 % 3].value
    assert records[0].reviewer == "Prüferin"
    assert records[0].note == "Kontrolle 53"
    assert "T" in records[0].reviewed_at_utc
    assert service.import_summary("P1").unreviewed_findings == 1
    assert len(service.pending_review_findings("P1")) == 1
    other = service.expert_review_history("P2")
    assert other.total == 1 and len(other.entries) == 1
    assert other.entries[0].note == "Isoliertes Projekt"
    assert all(r.note != "Isoliertes Projekt" for r in records)


def test_empty_and_invalid_history_queries_fail_closed(tmp_path):
    service = make_service(tmp_path, count=2)
    empty = service.expert_review_history("P1")
    assert empty.total == 0
    assert empty.entries == ()
    with pytest.raises(KeyError):
        service.expert_review_history("NOT-A-PROJECT")
    for invalid in (0, 51, -1, True, None, 1.5):
        with pytest.raises(ValueError, match="limit"):
            service.expert_review_history("P1", limit=invalid)
    for invalid in (-1, True, None, "3", 1.5):
        with pytest.raises(ValueError, match="offset"):
            service.expert_review_history("P1", offset=invalid)
    assert service.expert_review_history("P1", offset=25).entries == ()


def test_history_is_audit_read_only_and_never_changes_review_status(tmp_path):
    service = make_service(tmp_path, count=2)
    service.review_pending_finding(
        "P1", "F001", status=ReviewStatus.UNCLEAR,
        reviewer="Prüfer", note="Unsicher; weitere Prüfung",
    )
    with service.database.connect() as db:
        original = tuple(db.execute(
            "SELECT review_id, finding_id, status, reviewer, note "
            "FROM finding_reviews WHERE project_id='P1'",
        ))
    for _ in range(3):
        result = service.expert_review_history("P1")
        assert result.total == 1
        assert result.entries[0].status == "unclear"
    with service.database.connect() as db:
        assert tuple(db.execute(
            "SELECT review_id, finding_id, status, reviewer, note "
            "FROM finding_reviews WHERE project_id='P1'",
        )) == original
    assert service.import_summary("P1").unreviewed_findings == 1
    assert service.import_summary("P2").unreviewed_findings == 2


def test_historical_event_status_not_replaced_by_current_finding_state(tmp_path):
    service = make_service(tmp_path, count=1)
    service.review_pending_finding(
        "P1", "F001", status=ReviewStatus.REJECTED,
        reviewer="Prüfer", note="Abgewiesen",
    )
    # A prior event is immutable even if a legacy writer later modifies
    # the current finding status (this must not be used for actual review).
    with service.database.connect() as db:
        db.execute(
            "UPDATE findings SET reviewer_status='confirmed' "
            "WHERE project_id='P1' AND finding_id='F001'",
        )
    history = service.expert_review_history("P1")
    assert history.entries[0].status == "rejected"
    assert history.entries[0].note == "Abgewiesen"
