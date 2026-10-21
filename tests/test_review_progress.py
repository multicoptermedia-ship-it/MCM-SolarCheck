"""SQLite-backed, non-authorizing expert decision progress regressions."""
from dataclasses import replace
from pathlib import Path

import pytest

from mcm_solarcheck.domain.models import Finding, ThermalFrame
from mcm_solarcheck.review.findings import ReviewStatus
from mcm_solarcheck.services.project_pipeline import ProjectApplicationService
from mcm_solarcheck.services.review_progress import derive_review_progress
from mcm_solarcheck.storage.queries import InspectionSummary
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult


def summary(**changes):
    values = InspectionSummary(
        project_id="P1", rgb_frames=0, thermal_frames=0, image_pairs=0,
        pv_modules=0, findings=0, unreviewed_findings=0,
        confirmed_findings=0, rejected_findings=0, unclear_findings=0,
        calibrated_findings=0,
    )
    return replace(values, **changes)


@pytest.mark.parametrize("values,decided,percent,complete", [
    ({}, 0, 0, False),
    ({"findings": 4, "unreviewed_findings": 4}, 0, 0, False),
    ({"findings": 4, "confirmed_findings": 1, "rejected_findings": 1,
      "unclear_findings": 1, "unreviewed_findings": 1}, 3, 75, False),
    ({"findings": 4, "confirmed_findings": 1, "rejected_findings": 2,
      "unclear_findings": 1}, 4, 100, True),
    ({"findings": 3, "confirmed_findings": 1,
      "unreviewed_findings": 1}, 1, 33, False),
    ({"findings": 7, "confirmed_findings": 3,
      "rejected_findings": 3, "unclear_findings": 1}, 7, 100, True),
])
def test_percent_tracks_explicit_human_decisions_not_camera_or_module_counts(
    values, decided, percent, complete,
):
    result = derive_review_progress(summary(**values))
    assert result.decided_findings == decided
    assert result.decision_percent == percent
    assert result.all_findings_decided is complete
    assert result.project_id == "P1"
    assert "keine automatische Diagnose" in result.guidance[-1]


def test_no_findings_is_not_automatically_a_clean_inspection():
    progress = derive_review_progress(summary(rgb_frames=20, thermal_frames=20))
    assert progress.total_findings == 0
    assert progress.decision_percent == 0
    assert not progress.all_findings_decided
    assert any("weder eine abgeschlossene" in x for x in progress.guidance)
    assert all("mängelfreie" not in x for x in progress.guidance[-1:])


def test_unclear_is_decided_but_requires_explicit_followup_notice():
    progress = derive_review_progress(summary(
        findings=2, confirmed_findings=1, unclear_findings=1,
    ))
    assert progress.all_findings_decided
    assert progress.decision_percent == 100
    assert any("Nachprüfung" in text for text in progress.guidance)
    assert not any("Alle gespeicherten" in text for text in progress.guidance)


def test_unknown_status_cannot_be_reported_as_complete():
    progress = derive_review_progress(summary(
        findings=7, confirmed_findings=2, unreviewed_findings=1,
        rejected_findings=1, unclear_findings=1,
    ))
    assert progress.other_status_findings == 2
    assert progress.decided_findings == 4
    assert progress.decision_percent == 57
    assert not progress.all_findings_decided
    assert any("keinen bekannten Prüfstatus" in text for text in progress.guidance)


@pytest.mark.parametrize("values", [
    {"findings": -1},
    {"findings": 1, "confirmed_findings": 2},
    {"findings": 1, "unreviewed_findings": -1},
    {"findings": True},
    {"findings": 1, "unclear_findings": True},
    {"findings": 1, "rejected_findings": 1, "confirmed_findings": 1},
])
def test_inconsistent_counts_fail_instead_of_claiming_completion(values):
    with pytest.raises(ValueError, match="inconsistent"):
        derive_review_progress(summary(**values))


def test_does_not_accept_untrusted_freeform_status_counts():
    with pytest.raises(TypeError, match="InspectionSummary"):
        derive_review_progress({
            "project_id": "P1", "findings": 0, "confirmed_findings": 0,
        })


def prepared_service(tmp_path):
    database = ProjectDatabase(tmp_path / "projects.sqlite3")
    database.initialize()
    service = ProjectApplicationService(database)
    for project in ("P1", "P2"):
        service.create_project(project, "Synthetischer Solarpark")
        database.save_thermal_frame(
            project,
            ThermalFrame(
                frame_id="T1", source_file=Path("synthetic.JPG"),
                thermal_width=640, thermal_height=512, thermal_source="raw",
            ),
            ThermalQualityResult(
                ThermalQualityGrade.PASS, (),
                RawThermalStatistics(1, 10, 5.0, 5.0, 9.0, 10.0, 9),
            ),
        )
        database.save_findings(project, (
            Finding("F1", "T1", 2, 3, module_id="M1"),
            Finding("F2", "T1", 4, 5, module_id="M2"),
            Finding("F3", "T1", 6, 7, module_id="M3"),
        ))
    return service


def test_service_reflects_only_persisted_project_specific_decisions(tmp_path):
    service = prepared_service(tmp_path)
    assert service.review_progress("P1").open_findings == 3
    assert service.review_progress("P2").open_findings == 3

    service.review_pending_finding(
        "P1", "F1", status=ReviewStatus.CONFIRMED,
        reviewer="Pruefer A", note="Gesichtet",
    )
    service.review_pending_finding(
        "P1", "F2", status=ReviewStatus.REJECTED,
        reviewer="Pruefer A", note="Verworfen",
    )
    first = service.review_progress("P1")
    assert first.total_findings == 3
    assert first.decided_findings == 2
    assert first.open_findings == 1
    assert first.confirmed_findings == 1
    assert first.rejected_findings == 1
    assert first.unclear_findings == 0
    assert first.decision_percent == 66
    assert not first.all_findings_decided
    assert service.review_progress("P2").decision_percent == 0

    service.review_pending_finding(
        "P1", "F3", status=ReviewStatus.UNCLEAR,
        reviewer="Pruefer B", note="Weitere Abklärung erforderlich",
    )
    final = service.review_progress("P1")
    assert final.decision_percent == 100
    assert final.open_findings == 0
    assert final.unclear_findings == 1
    assert final.all_findings_decided
    assert any("Nachprüfung" in x for x in final.guidance)
    assert service.review_progress("P2").open_findings == 3
    with service.database.connect() as db:
        assert db.execute(
            "SELECT COUNT(*) FROM finding_reviews WHERE project_id='P1'",
        ).fetchone()[0] == 3


def test_service_read_only_and_unknown_project_rejected(tmp_path):
    service = prepared_service(tmp_path)
    with pytest.raises(KeyError, match="Unknown project"):
        service.review_progress("MISSING")
    with service.database.connect() as db:
        prior = db.execute(
            "SELECT COUNT(*) FROM finding_reviews WHERE project_id='P1'",
        ).fetchone()[0]
    for _ in range(3):
        assert service.review_progress("P1").open_findings == 3
    with service.database.connect() as db:
        assert db.execute(
            "SELECT COUNT(*) FROM finding_reviews WHERE project_id='P1'",
        ).fetchone()[0] == prior
