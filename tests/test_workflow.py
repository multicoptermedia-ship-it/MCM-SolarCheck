from __future__ import annotations

import pytest

from mcm_solarcheck.services.workflow import (ProjectWorkflowService, WorkflowAction, WorkflowAttempt, WorkflowStage, action_availability, record_attempt, require_action, resume_point)
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from mcm_solarcheck.services.project_pipeline import ProjectApplicationService


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


def _database_with_finding(tmp_path, *, status, module_id):
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
    database.save_findings(
        "P1",
        (Finding("F1", "T1", 1, 2, module_id=module_id, reviewer_status=status),),
    )
    return database


@pytest.mark.parametrize("status", ["confirmed", "unclear"])
def test_reviewed_finding_without_module_blocks_report_and_export(tmp_path, status):
    state = ProjectWorkflowService(
        _database_with_finding(tmp_path, status=status, module_id=None)
    ).state("P1")

    blocker = "reviewed findings require resolved physical modules"
    assert blocker in state.readiness(WorkflowStage.REPORT).blockers
    assert blocker in state.readiness(WorkflowStage.EXPORT).blockers


@pytest.mark.parametrize("status", ["confirmed", "unclear"])
def test_reviewed_finding_with_module_allows_report_and_export(tmp_path, status):
    state = ProjectWorkflowService(
        _database_with_finding(tmp_path, status=status, module_id="M1")
    ).state("P1")

    assert state.readiness(WorkflowStage.REVIEW).ready is True
    assert state.readiness(WorkflowStage.REPORT).ready is True
    assert state.readiness(WorkflowStage.EXPORT).ready is True


def test_resume_point_returns_first_blocked_stage(tmp_path):
    state = ProjectWorkflowService(_database(tmp_path)).state("P1")
    resume = resume_point(state)
    assert resume.stage is WorkflowStage.IMPORT
    assert resume.blockers == ("no imported image frames",)


def test_resume_point_moves_to_review_after_import(tmp_path):
    database = _database_with_finding(tmp_path, status="unreviewed", module_id="M1")
    state = ProjectWorkflowService(database).state("P1")
    resume = resume_point(state)
    assert resume.stage is WorkflowStage.REPORT
    assert resume.blockers == ("unreviewed findings remain",)


def test_resume_point_finishes_at_export_when_workflow_is_ready(tmp_path):
    database = _database_with_finding(tmp_path, status="confirmed", module_id="M1")
    state = ProjectWorkflowService(database).state("P1")
    resume = resume_point(state)
    assert resume.stage is WorkflowStage.EXPORT
    assert resume.blockers == ()


def test_actions_are_derived_from_persisted_readiness(tmp_path):
    state = ProjectWorkflowService(_database(tmp_path)).state("P1")

    assert action_availability(state, WorkflowAction.IMPORT).allowed is True
    process = action_availability(state, WorkflowAction.PROCESS)
    assert process.allowed is False
    assert process.blockers == ("no imported image frames",)


def test_blocked_action_fails_closed_with_reason(tmp_path):
    state = ProjectWorkflowService(_database(tmp_path)).state("P1")

    with pytest.raises(ValueError, match="process action is blocked: no imported image frames"):
        require_action(state, WorkflowAction.PROCESS)


def test_ready_reviewed_project_allows_report_and_export_actions(tmp_path):
    database = _database_with_finding(tmp_path, status="confirmed", module_id="M1")
    state = ProjectWorkflowService(database).state("P1")

    assert action_availability(state, WorkflowAction.REVIEW).allowed is True
    assert action_availability(state, WorkflowAction.PREPARE_REPORT).allowed is True
    assert action_availability(state, WorkflowAction.EXPORT).allowed is True
    require_action(state, WorkflowAction.EXPORT)


def test_application_service_exposes_persisted_state(tmp_path):
    database = _database(tmp_path)
    service = ProjectApplicationService(database)

    state = service.state("P1")

    assert state.readiness(WorkflowStage.PROJECT).ready is True
    assert state.readiness(WorkflowStage.IMPORT).ready is False


def test_application_service_rejects_blocked_action_before_caller_side_effect(tmp_path):
    database = _database(tmp_path)
    service = ProjectApplicationService(database)
    side_effects = []

    with pytest.raises(ValueError, match="process action is blocked"):
        service.require("P1", WorkflowAction.PROCESS)
        side_effects.append("processing-started")

    assert side_effects == []


def test_application_service_allows_action_only_after_persisted_prerequisite(tmp_path):
    database = _database_with_finding(tmp_path, status="confirmed", module_id="M1")
    service = ProjectApplicationService(database)

    service.require("P1", WorkflowAction.EXPORT)


def test_failed_attempt_does_not_advance_persisted_workflow(tmp_path):
    database = _database(tmp_path)
    service = ProjectApplicationService(database)
    before = service.state("P1")

    attempt = record_attempt(WorkflowAction.IMPORT, RuntimeError("source unavailable"))

    after = service.state("P1")
    assert attempt == WorkflowAttempt(WorkflowAction.IMPORT, False, "source unavailable")
    assert after == before
    assert after.readiness(WorkflowStage.IMPORT).ready is False


def test_successful_attempt_alone_does_not_replace_persisted_evidence(tmp_path):
    database = _database(tmp_path)
    service = ProjectApplicationService(database)

    attempt = record_attempt(WorkflowAction.IMPORT)

    assert attempt == WorkflowAttempt(WorkflowAction.IMPORT, True)
    assert service.state("P1").readiness(WorkflowStage.IMPORT).ready is False


def test_failed_attempt_requires_action_and_error_contract():
    with pytest.raises(ValueError, match="failed attempt requires"):
        WorkflowAttempt(WorkflowAction.PROCESS, False, None)

    with pytest.raises(ValueError, match="successful attempt must not carry"):
        WorkflowAttempt(WorkflowAction.PROCESS, True, "unexpected")


def test_execute_success_rederives_state_from_persisted_operation(tmp_path):
    from pathlib import Path
    from mcm_solarcheck.domain.models import ThermalFrame
    from mcm_solarcheck.thermal.analysis import RawThermalStatistics
    from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult

    database = _database(tmp_path)
    service = ProjectApplicationService(database)

    def persist_import():
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
        return "stored"

    attempt, result, state = service.execute("P1", WorkflowAction.IMPORT, persist_import)

    assert attempt == WorkflowAttempt(WorkflowAction.IMPORT, True)
    assert result == "stored"
    assert state.readiness(WorkflowStage.IMPORT).ready is True
    assert state.readiness(WorkflowStage.PROCESSING).ready is True


def test_execute_failure_rederives_unchanged_persisted_state(tmp_path):
    database = _database(tmp_path)
    service = ProjectApplicationService(database)

    def fail_import():
        raise RuntimeError("reader failed")

    attempt, result, state = service.execute("P1", WorkflowAction.IMPORT, fail_import)

    assert attempt == WorkflowAttempt(WorkflowAction.IMPORT, False, "reader failed")
    assert result is None
    assert state.readiness(WorkflowStage.IMPORT).ready is False
    assert state.readiness(WorkflowStage.PROCESSING).ready is False


def test_execute_does_not_call_operation_when_guard_is_blocked(tmp_path):
    database = _database(tmp_path)
    service = ProjectApplicationService(database)
    calls = []

    with pytest.raises(ValueError, match="process action is blocked"):
        service.execute(
            "P1",
            WorkflowAction.PROCESS,
            lambda: calls.append("called"),
        )

    assert calls == []

def test_application_output_availability_combines_trial_and_persisted_export_gate(tmp_path):
    from mcm_solarcheck.services.product_entitlements import (
        PROMOTIONAL_TRIAL,
        ProductOperation,
    )

    database = _database_with_finding(tmp_path, status="unreviewed", module_id="M1")
    availability = ProjectApplicationService(database).output_availability(
        "P1", PROMOTIONAL_TRIAL, ProductOperation.EXPORT
    )

    assert availability.allowed is False
    assert availability.blockers == (
        "promotional_trial does not permit export",
        "unreviewed findings remain",
    )


def test_application_output_availability_allows_ready_full_online_export(tmp_path):
    from mcm_solarcheck.services.product_entitlements import (
        FULL_ONLINE,
        ProductOperation,
    )

    database = _database_with_finding(tmp_path, status="confirmed", module_id="M1")
    availability = ProjectApplicationService(database).output_availability(
        "P1", FULL_ONLINE, ProductOperation.EXPORT
    )

    assert availability.allowed is True
    assert availability.blockers == ()

