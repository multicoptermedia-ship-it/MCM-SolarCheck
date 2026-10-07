from __future__ import annotations

from datetime import datetime, timezone

import pytest
from unittest.mock import patch

from mcm_solarcheck.infrastructure.filesystem_report import FileSystemReportArtifactStore
from mcm_solarcheck.infrastructure.sqlite_billing import SQLiteComputeJobBillingStore
from mcm_solarcheck.reporting.report_model import InspectionReport
from mcm_solarcheck.services.billing import ComputeJobBillingService
from mcm_solarcheck.services.private_report_export import PrivateReportExportService


def report(project_id: str = "project-a") -> InspectionReport:
    return InspectionReport(
        "report-a",
        project_id,
        "Customer",
        "Site",
        datetime(2026, 9, 30, 12, tzinfo=timezone.utc),
        "Inspector",
        10,
        0,
        0,
    )


def setup_export(tmp_path):
    billing_store = SQLiteComputeJobBillingStore(tmp_path / "billing.sqlite")
    billing = ComputeJobBillingService(billing_store)
    billing.create("job-a", user_id="user-a", project_id="project-a")
    artifacts = FileSystemReportArtifactStore(tmp_path / "private" / "reports")
    return billing_store, artifacts, PrivateReportExportService(billing_store, artifacts)


def test_successful_export_writes_private_artifact_then_marks_complete(tmp_path) -> None:
    billing, artifacts, service = setup_export(tmp_path)

    state = service.export(
        report(),
        "job-a",
        user_id="user-a",
        project_id="project-a",
    )

    assert artifacts.path_for("job-a").is_file()
    assert state.delivery.export_completed is True
    assert billing.get("job-a").delivery.export_completed is True


def test_failed_export_never_marks_export_complete(tmp_path) -> None:
    billing, artifacts, service = setup_export(tmp_path)

    with pytest.raises(FileNotFoundError):
        service.export(
            report(),
            "job-a",
            user_id="user-a",
            project_id="project-a",
            banner_path=tmp_path / "missing-banner.png",
        )

    assert artifacts.path_for("job-a").exists() is False
    assert billing.get("job-a").delivery.export_completed is False


def test_export_rejects_wrong_project_before_writing_artifact(tmp_path) -> None:
    billing, artifacts, service = setup_export(tmp_path)

    with pytest.raises(ValueError, match="project"):
        service.export(
            report("project-b"),
            "job-a",
            user_id="user-a",
            project_id="project-a",
        )

    assert artifacts.path_for("job-a").exists() is False
    assert billing.get("job-a").delivery.export_completed is False


def test_export_rejects_wrong_user_before_writing_artifact(tmp_path) -> None:
    billing, artifacts, service = setup_export(tmp_path)

    with pytest.raises(PermissionError, match="ownership"):
        service.export(
            report(),
            "job-a",
            user_id="user-b",
            project_id="project-a",
        )

    assert artifacts.path_for("job-a").exists() is False
    assert billing.get("job-a").delivery.export_completed is False


def test_partial_failed_export_never_publishes_final_report(tmp_path) -> None:
    billing, artifacts, service = setup_export(tmp_path)

    def fail_after_partial_write(report, destination, **kwargs) -> None:
        destination.write_bytes(b"partial report")
        raise RuntimeError("renderer failed")

    with patch(
        "mcm_solarcheck.services.private_report_export.export_report",
        side_effect=fail_after_partial_write,
    ):
        with pytest.raises(RuntimeError, match="renderer failed"):
            service.export(
                report(),
                "job-a",
                user_id="user-a",
                project_id="project-a",
            )

    assert artifacts.path_for("job-a").exists() is False
    assert list(artifacts.root.glob(".*.tmp")) == []
    assert billing.get("job-a").delivery.export_completed is False


def test_atomic_export_publishes_only_final_report_name(tmp_path) -> None:
    billing, artifacts, service = setup_export(tmp_path)

    service.export(
        report(),
        "job-a",
        user_id="user-a",
        project_id="project-a",
    )

    assert artifacts.path_for("job-a").is_file()
    assert list(artifacts.root.glob(".*.tmp")) == []
    assert billing.get("job-a").delivery.export_completed is True


def test_export_publishes_through_report_store_boundary(tmp_path, monkeypatch) -> None:
    billing, artifacts, service = setup_export(tmp_path)
    published = []
    original_publish = artifacts.publish

    def tracked_publish(job_id, temporary):
        published.append(job_id)
        return original_publish(job_id, temporary)

    monkeypatch.setattr(artifacts, "publish", tracked_publish)

    state = service.export(
        report(),
        "job-a",
        user_id="user-a",
        project_id="project-a",
    )

    assert published == ["job-a"]
    assert artifacts.get("job-a").content
    assert state.delivery.export_completed is True
