from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.sqlite_billing import SQLiteComputeJobBillingStore
from mcm_solarcheck.services.billing import ComputeJobBillingService
from mcm_solarcheck.services.report_delivery import ReportArtifact, ReportDeliveryService


class RecordingReportStore:
    def __init__(self) -> None:
        self.reads = 0

    def get(self, job_id: str) -> ReportArtifact:
        self.reads += 1
        return ReportArtifact(
            job_id,
            b"confidential SolarCheck report",
            "application/pdf",
            "solarcheck.pdf",
        )


def test_report_bytes_are_not_readable_before_export(tmp_path) -> None:
    store = SQLiteComputeJobBillingStore(tmp_path / "billing.sqlite")
    ComputeJobBillingService(store).create(
        "job-a", user_id="user-a", project_id="project-a"
    )
    reports = RecordingReportStore()
    delivery = ReportDeliveryService(store, reports)

    with pytest.raises(ValueError, match="unavailable until export"):
        delivery.retrieve(
            "job-a",
            user_id="user-a",
            project_id="project-a",
        )

    assert reports.reads == 0


def test_report_becomes_readable_only_after_export(tmp_path) -> None:
    store = SQLiteComputeJobBillingStore(tmp_path / "billing.sqlite")
    billing = ComputeJobBillingService(store)
    billing.create("job-a", user_id="user-a", project_id="project-a")
    reports = RecordingReportStore()
    delivery = ReportDeliveryService(store, reports)

    billing.mark_export_completed(
        "job-a", user_id="user-a", project_id="project-a"
    )
    report = delivery.retrieve(
        "job-a",
        user_id="user-a",
        project_id="project-a",
    )

    assert report.content == b"confidential SolarCheck report"
    assert reports.reads == 1


def test_report_access_rejects_other_tenant_before_reading_artifact(tmp_path) -> None:
    store = SQLiteComputeJobBillingStore(tmp_path / "billing.sqlite")
    billing = ComputeJobBillingService(store)
    billing.create("job-a", user_id="user-a", project_id="project-a")
    billing.mark_export_completed(
        "job-a", user_id="user-a", project_id="project-a"
    )
    reports = RecordingReportStore()
    delivery = ReportDeliveryService(store, reports)

    with pytest.raises(PermissionError, match="ownership mismatch"):
        delivery.retrieve(
            "job-a",
            user_id="user-b",
            project_id="project-a",
        )

    assert reports.reads == 0
