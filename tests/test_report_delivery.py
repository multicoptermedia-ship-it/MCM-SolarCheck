from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.sqlite_billing import SQLiteComputeJobBillingStore
from mcm_solarcheck.services.billing import ComputeJobBillingService
from mcm_solarcheck.services.report_delivery import ReportArtifact, ReportDeliveryService


class RecordingReportStore:
    def __init__(self, *, artifact_job_id: str = "job-a") -> None:
        self.reads = 0
        self.artifact_job_id = artifact_job_id

    def get(self, job_id: str) -> ReportArtifact:
        self.reads += 1
        return ReportArtifact(
            self.artifact_job_id,
            b"confidential SolarCheck report",
            "application/pdf",
            "solarcheck.pdf",
        )


def setup_delivery(tmp_path):
    store = SQLiteComputeJobBillingStore(tmp_path / "billing.sqlite")
    billing = ComputeJobBillingService(store)
    billing.create("job-a", user_id="user-a", project_id="project-a")
    reports = RecordingReportStore()
    return store, billing, reports, ReportDeliveryService(store, reports)


def test_report_bytes_are_not_readable_before_export(tmp_path) -> None:
    store, _billing, reports, delivery = setup_delivery(tmp_path)

    with pytest.raises(ValueError, match="unavailable until export"):
        delivery.retrieve(
            "job-a",
            user_id="user-a",
            project_id="project-a",
        )

    assert reports.reads == 0
    assert store.get("job-a").delivery.report_retrieved is False
    assert store.get("job-a").billing_released is False


def test_report_becomes_readable_only_after_export(tmp_path) -> None:
    store, billing, reports, delivery = setup_delivery(tmp_path)
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
    assert store.get("job-a").delivery.report_retrieved is False
    assert store.get("job-a").billing_released is False


def test_report_access_rejects_other_tenant_before_reading_artifact(tmp_path) -> None:
    store, billing, reports, delivery = setup_delivery(tmp_path)
    billing.mark_export_completed(
        "job-a", user_id="user-a", project_id="project-a"
    )

    with pytest.raises(PermissionError, match="ownership mismatch"):
        delivery.retrieve(
            "job-a",
            user_id="user-b",
            project_id="project-a",
        )

    assert reports.reads == 0
    assert store.get("job-a").billing_released is False


def test_successful_delivery_persists_evidence_then_releases_billing(tmp_path) -> None:
    store, billing, _reports, delivery = setup_delivery(tmp_path)
    billing.mark_export_completed(
        "job-a", user_id="user-a", project_id="project-a"
    )
    sent = []

    released = delivery.deliver(
        "job-a",
        user_id="user-a",
        project_id="project-a",
        send=sent.append,
    )

    assert len(sent) == 1
    assert sent[0].content == b"confidential SolarCheck report"
    assert released.delivery.report_retrieved is True
    assert released.billing_released is True
    assert store.get("job-a") == released


def test_failed_delivery_never_persists_evidence_or_releases_billing(tmp_path) -> None:
    store, billing, _reports, delivery = setup_delivery(tmp_path)
    billing.mark_export_completed(
        "job-a", user_id="user-a", project_id="project-a"
    )

    def fail(_report: ReportArtifact) -> None:
        raise OSError("client disconnected")

    with pytest.raises(OSError, match="client disconnected"):
        delivery.deliver(
            "job-a",
            user_id="user-a",
            project_id="project-a",
            send=fail,
        )

    persisted = store.get("job-a")
    assert persisted.delivery.report_retrieved is False
    assert persisted.billing_released is False


def test_wrong_report_artifact_never_reaches_transport_or_billing(tmp_path) -> None:
    store = SQLiteComputeJobBillingStore(tmp_path / "billing.sqlite")
    billing = ComputeJobBillingService(store)
    billing.create("job-a", user_id="user-a", project_id="project-a")
    billing.mark_export_completed(
        "job-a", user_id="user-a", project_id="project-a"
    )
    delivery = ReportDeliveryService(
        store,
        RecordingReportStore(artifact_job_id="job-b"),
    )
    sent = []

    with pytest.raises(ValueError, match="does not belong"):
        delivery.deliver(
            "job-a",
            user_id="user-a",
            project_id="project-a",
            send=sent.append,
        )

    assert sent == []
    persisted = store.get("job-a")
    assert persisted.delivery.report_retrieved is False
    assert persisted.billing_released is False


def test_repeated_successful_delivery_is_billing_idempotent(tmp_path) -> None:
    store, billing, _reports, delivery = setup_delivery(tmp_path)
    billing.mark_export_completed(
        "job-a", user_id="user-a", project_id="project-a"
    )
    sent = []

    first = delivery.deliver(
        "job-a",
        user_id="user-a",
        project_id="project-a",
        send=sent.append,
    )
    second = delivery.deliver(
        "job-a",
        user_id="user-a",
        project_id="project-a",
        send=sent.append,
    )

    assert len(sent) == 2
    assert first.billing_released is True
    assert second == first
    assert store.get("job-a") == first


def test_failed_attempt_can_retry_once_then_release_billing(tmp_path) -> None:
    store, billing, _reports, delivery = setup_delivery(tmp_path)
    billing.mark_export_completed(
        "job-a", user_id="user-a", project_id="project-a"
    )
    attempts = 0

    def flaky(_report: ReportArtifact) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("client disconnected")

    with pytest.raises(OSError, match="client disconnected"):
        delivery.deliver(
            "job-a",
            user_id="user-a",
            project_id="project-a",
            send=flaky,
        )

    blocked = store.get("job-a")
    assert blocked.delivery.report_retrieved is False
    assert blocked.billing_released is False

    released = delivery.deliver(
        "job-a",
        user_id="user-a",
        project_id="project-a",
        send=flaky,
    )

    assert attempts == 2
    assert released.delivery.report_retrieved is True
    assert released.billing_released is True
