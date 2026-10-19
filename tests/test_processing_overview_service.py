"""Read-only processing overview reuses persisted SQLite counts and workflow gates."""
from pathlib import Path

import pytest

from mcm_solarcheck.domain.models import Finding, ThermalFrame
from mcm_solarcheck.services.project_pipeline import (
    ProjectApplicationService, ProjectProcessingOverview,
)
from mcm_solarcheck.services.workflow import WorkflowAction, WorkflowStage
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult


def project_service(tmp_path):
    database = ProjectDatabase(tmp_path / "project.sqlite")
    database.initialize()
    database.create_project("P1", "Project Alpha")
    database.create_project("P2", "Project Beta")
    return ProjectApplicationService(database)


def test_processing_overview_is_project_scoped_and_import_gated(tmp_path):
    service = project_service(tmp_path)
    result = service.processing_overview("P1")

    assert isinstance(result, ProjectProcessingOverview)
    assert result.summary.project_id == "P1"
    assert result.summary.rgb_frames == 0
    assert result.summary.thermal_frames == 0
    assert result.summary.image_pairs == 0
    assert result.summary.pv_modules == 0
    assert result.summary.findings == 0
    assert result.process.action is WorkflowAction.PROCESS
    assert result.process.allowed is False
    assert result.process.blockers == ("no imported image frames",)
    assert result.review.action is WorkflowAction.REVIEW
    assert result.review.allowed is False
    assert result.review.blockers == ("no processed modules or findings",)
    assert service.processing_overview("P2").summary.project_id == "P2"

    with pytest.raises(KeyError, match="Unknown project"):
        service.processing_overview("unknown")


def test_imported_thermal_frame_shows_evidence_but_not_completed_analysis(tmp_path):
    service = project_service(tmp_path)
    frame = ThermalFrame(
        frame_id="T1",
        source_file=Path("T1.JPG"),
        thermal_width=640,
        thermal_height=512,
        thermal_source="raw",
    )
    quality = ThermalQualityResult(
        ThermalQualityGrade.PASS,
        (),
        RawThermalStatistics(1, 10, 5.0, 5.0, 9.0, 10.0, 9),
    )
    service.database.save_thermal_frame("P1", frame, quality)

    result = service.processing_overview("P1")
    assert result.summary.thermal_frames == 1
    assert result.summary.findings == 0
    assert result.process.allowed
    assert result.review.allowed is False
    assert result.review.blockers == ("no processed modules or findings",)
    assert service.processing_overview("P2").summary.thermal_frames == 0


def test_persisted_unreviewed_candidate_does_not_imply_expert_approval(tmp_path):
    service = project_service(tmp_path)
    frame = ThermalFrame(
        frame_id="T1",
        source_file=Path("T1.JPG"),
        thermal_width=640,
        thermal_height=512,
        thermal_source="raw",
    )
    quality = ThermalQualityResult(
        ThermalQualityGrade.PASS,
        (),
        RawThermalStatistics(1, 10, 5.0, 5.0, 9.0, 10.0, 9),
    )
    service.database.save_thermal_frame("P1", frame, quality)
    service.database.save_findings(
        "P1", (Finding("F1", "T1", 1, 2, reviewer_status="unreviewed"),),
    )

    overview = service.processing_overview("P1")
    assert overview.summary.findings == 1
    assert overview.summary.unreviewed_findings == 1
    assert overview.summary.confirmed_findings == 0
    assert overview.review.allowed
    assert service.state("P1").readiness(WorkflowStage.REPORT).ready is False
    assert service.state("P1").readiness(WorkflowStage.EXPORT).ready is False
