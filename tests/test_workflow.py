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
