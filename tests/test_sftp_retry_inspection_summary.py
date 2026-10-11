import pytest

from mcm_solarcheck.services.queued_job_dispatcher import PendingProjectJob
from mcm_solarcheck.services.queued_sftp_preflight import QueuedSFTPInspection
from mcm_solarcheck.services.explicit_queued_sftp_preflight_retry import RetryPreflightResult
from mcm_solarcheck.services.sftp_retry_inspection_summary import summarize_retry_inspection


def test_summary_ready_missing_and_wait():
    job = PendingProjectJob(customer_id="c", project_id="p", job_id="j")
    ready = QueuedSFTPInspection("j", "c", "p", True)
    missing = QueuedSFTPInspection("j", "c", "p", False)
    assert summarize_retry_inspection(job, RetryPreflightResult("inspected", ready)).status == "ready"
    assert summarize_retry_inspection(job, RetryPreflightResult("inspected", missing)).status == "missing_directory"
    assert summarize_retry_inspection(job, RetryPreflightResult("wait")).status == "wait"


def test_summary_rejects_foreign_inspection_and_unexpected_result():
    job = PendingProjectJob(customer_id="c", project_id="p", job_id="j")
    foreign = QueuedSFTPInspection("j", "other", "p", True)
    with pytest.raises(PermissionError):
        summarize_retry_inspection(job, RetryPreflightResult("inspected", foreign))
    with pytest.raises(ValueError):
        summarize_retry_inspection(job, RetryPreflightResult("failed", None))
    with pytest.raises(ValueError):
        summarize_retry_inspection(job, RetryPreflightResult("busy", foreign))
    with pytest.raises(TypeError):
        summarize_retry_inspection(job, RetryPreflightResult("inspected", "unverified"))
