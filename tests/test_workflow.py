from __future__ import annotations

import pytest

from mcm_solarcheck.services.workflow import ProjectWorkflowService, WorkflowStage
from mcm_solarcheck.storage.sqlite import ProjectDatabase


def _database(tmp_path):
    database = ProjectDatabase(tmp_path / "project.sqlite")
    database.initialize()
    database.create_project("P1", "Project")
    return database


def test_empty_project_is_fail_closed(tmp_path):
    state = ProjectWorkflowService(_database(tmp_path)).state("P1")

    assert state.readiness(WorkflowStage.PROJECT).ready is True
    assert state.readiness(WorkflowStage.IMPORT).blockers == ("no imported image frames",)
    assert state.readiness(WorkflowStage.PROCESSING).blockers == ("import required before processing",)
    assert state.readiness(WorkflowStage.REVIEW).blockers == ("no processed modules or findings",)
    assert state.readiness(WorkflowStage.REPORT).ready is False
    assert state.readiness(WorkflowStage.EXPORT).ready is False


def test_unknown_project_is_rejected(tmp_path):
    with pytest.raises(KeyError, match="Unknown project"):
        ProjectWorkflowService(_database(tmp_path)).state("missing")


def test_imported_project_opens_processing_but_not_review(tmp_path):
    from pathlib import Path
    from mcm_solarcheck.domain.models import ThermalFrame
    from mcm_solarcheck.thermal.analysis import RawThermalStatistics
    from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult

    database = _database(tmp_path)
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
    database.save_thermal_frame("P1", frame, quality)

    state = ProjectWorkflowService(database).state("P1")
    assert state.readiness(WorkflowStage.IMPORT).ready is True
    assert state.readiness(WorkflowStage.PROCESSING).ready is True
    assert state.readiness(WorkflowStage.REVIEW).ready is False
    assert state.readiness(WorkflowStage.REPORT).ready is False
    assert state.readiness(WorkflowStage.EXPORT).ready is False


def test_unreviewed_finding_blocks_report_and_export(tmp_path):
    from pathlib import Path
    from mcm_solarcheck.domain.models import Finding, ThermalFrame
    from mcm_solarcheck.thermal.analysis import RawThermalStatistics
    from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult

    database = _database(tmp_path)
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
    database.save_thermal_frame("P1", frame, quality)
    database.save_findings("P1", (Finding("F1", "T1", 1, 2, reviewer_status="unreviewed"),))

    state = ProjectWorkflowService(database).state("P1")
    assert state.readiness(WorkflowStage.REVIEW).ready is True
    assert state.readiness(WorkflowStage.REPORT).blockers == ("unreviewed findings remain",)
    assert state.readiness(WorkflowStage.EXPORT).blockers == ("unreviewed findings remain",)
