"""Persisted PV-module overview: bounded evidence, isolated project scope, no geometry claims."""
from pathlib import Path

import pytest

from mcm_solarcheck.domain.models import Finding, PVModule, ThermalFrame
from mcm_solarcheck.services.project_pipeline import PlantOverview, ProjectApplicationService
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult
from mcm_solarcheck.vision.module_identity import IdentityAssignment, ModuleObservation


def _frame(db, project):
    frame = ThermalFrame(
        frame_id="T1", source_file=Path("T1.JPG"),
        thermal_width=640, thermal_height=512, thermal_source="raw",
    )
    grade = ThermalQualityResult(
        ThermalQualityGrade.PASS, (),
        RawThermalStatistics(1, 10, 5.0, 5.0, 9.0, 10.0, 9),
    )
    db.save_thermal_frame(project, frame, grade)


def seeded_service(tmp_path):
    db = ProjectDatabase(tmp_path / "pv-overview.sqlite3")
    db.initialize()
    db.create_project("P1", "Solarpark Nord")
    db.create_project("P2", "Solarpark Sued")
    for project in ("P1", "P2"):
        _frame(db, project)
    m1 = PVModule("V:M1", "V", ((0, 0), (10, 0), (10, 20)), .9, "image-detector")
    m2 = PVModule("V:M2", "V", ((20, 0), (30, 0), (30, 20)), .8, "image-detector")
    db.save_modules("P1", (m2, m1))
    assignment = IdentityAssignment(
        ModuleObservation("V", "V:M1", (5, 10), 10, 20),
        "M-0001", "new", None,
    )
    db.save_module_identity_assignments("P1", (assignment,))
    db.save_findings("P1", (
        Finding("F1", "T1", 1, 1, module_id="V:M1", reviewer_status="confirmed"),
        Finding("F2", "T1", 2, 2, module_id="V:M1", reviewer_status="unreviewed"),
        Finding("F3", "T1", 3, 3, module_id="V:M2", reviewer_status="unclear"),
        Finding("F4", "T1", 4, 4, module_id=None, reviewer_status="unreviewed"),
        Finding("F5", "T1", 5, 5, module_id="missing", reviewer_status="confirmed"),
    ))
    db.save_modules("P2", (m1,))
    db.save_findings("P2", (
        Finding("F1", "T1", 9, 9, module_id="V:M1", reviewer_status="rejected"),
    ))
    return ProjectApplicationService(db)


def test_local_module_evidence_is_project_scoped_with_review_counts(tmp_path):
    service = seeded_service(tmp_path)
    overview = service.plant_overview("P1")
    assert isinstance(overview, PlantOverview)
    assert overview.summary.project_id == "P1"
    assert overview.summary.pv_modules == 2
    assert overview.summary.findings == 5
    assert overview.unassigned_findings == 2
    assert overview.offset == 0 and overview.limit == 100
    assert len(overview.modules) == 2
    a, b = overview.modules
    assert a.module_id == "V:M1"
    assert a.frame_id == "V"
    assert a.detector == "image-detector"
    assert a.detection_confidence == .9
    assert a.proposed_physical_id == "M-0001"
    assert a.identity_status == "new"
    assert (a.findings, a.unreviewed, a.confirmed, a.rejected, a.unclear) == (2, 1, 1, 0, 0)
    assert b.module_id == "V:M2"
    assert b.proposed_physical_id is None
    assert b.identity_status is None
    assert (b.findings, b.unreviewed, b.confirmed, b.rejected, b.unclear) == (1, 0, 0, 0, 1)
    assert sum(m.findings for m in overview.modules) + overview.unassigned_findings == overview.summary.findings

    other = service.plant_overview("P2")
    assert other.summary.project_id == "P2"
    assert other.summary.pv_modules == 1
    assert other.unassigned_findings == 0
    assert len(other.modules) == 1
    assert other.modules[0].proposed_physical_id is None
    assert (other.modules[0].findings, other.modules[0].rejected) == (1, 1)


def test_pagination_and_empty_page_keep_overall_counts(tmp_path):
    service = seeded_service(tmp_path)
    first = service.plant_overview("P1", limit=1, offset=0)
    second = service.plant_overview("P1", limit=1, offset=1)
    end = service.plant_overview("P1", limit=1, offset=2)
    assert [m.module_id for m in first.modules] == ["V:M1"]
    assert [m.module_id for m in second.modules] == ["V:M2"]
    assert end.modules == ()
    for overview in (first, second, end):
        assert overview.summary.pv_modules == 2
        assert overview.summary.findings == 5
        assert overview.unassigned_findings == 2
    assert service.plant_overview("P2", offset=999).modules == ()


@pytest.mark.parametrize("limit,offset", [
    (0, 0), (101, 0), (-1, 0), (True, 0), (1.5, 0),
    (1, -1), (1, False), (1, 1.5),
])
def test_invalid_page_parameters_rejected_before_query(tmp_path, limit, offset):
    service = seeded_service(tmp_path)
    with pytest.raises(ValueError, match="module page"):
        service.plant_overview("P1", limit=limit, offset=offset)


def test_unknown_project_is_rejected_and_query_is_read_only(tmp_path):
    service = seeded_service(tmp_path)
    with pytest.raises(KeyError, match="Unknown project"):
        service.plant_overview("unknown")
    with service.database.connect() as db:
        before = tuple(db.execute(
            "SELECT project_id,finding_id,reviewer_status FROM findings "
            "ORDER BY project_id,finding_id"
        ).fetchall())
    for _ in range(3):
        service.plant_overview("P1", limit=1)
    with service.database.connect() as db:
        after = tuple(db.execute(
            "SELECT project_id,finding_id,reviewer_status FROM findings "
            "ORDER BY project_id,finding_id"
        ).fetchall())
        assert db.execute("SELECT COUNT(*) FROM finding_reviews").fetchone()[0] == 0
    assert [tuple(row) for row in before] == [tuple(row) for row in after]


def test_findings_remain_visible_without_any_module_detection(tmp_path):
    db = ProjectDatabase(tmp_path / "only-findings.sqlite3")
    db.initialize()
    db.create_project("P1", "No module detection")
    _frame(db, "P1")
    db.save_findings("P1", (
        Finding("F1", "T1", 1, 2, reviewer_status="unreviewed"),
    ))
    overview = ProjectApplicationService(db).plant_overview("P1")
    assert overview.modules == ()
    assert overview.summary.pv_modules == 0
    assert overview.summary.findings == 1
    assert overview.unassigned_findings == 1
