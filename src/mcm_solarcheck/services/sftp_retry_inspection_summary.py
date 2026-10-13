"""Sanitized, owner-scoped classification of an explicit retry inspection result.

No retry attempts are recorded and no queue or remote state is changed.
"""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.explicit_queued_sftp_preflight_retry import RetryPreflightResult
from mcm_solarcheck.services.queued_sftp_preflight import QueuedSFTPInspection


@dataclass(frozen=True)
class RetryInspectionSummary:
    job_id: str
    customer_id: str
    project_id: str
    status: str


def summarize_retry_inspection(job, result: RetryPreflightResult) -> RetryInspectionSummary:
    if not isinstance(result, RetryPreflightResult):
        raise TypeError("RetryPreflightResult required")
    if result.status != "inspected":
        if result.inspection is not None:
            raise ValueError("non-inspected result must not carry inspection")
        if result.status not in ("unrecorded", "manual_review", "wait", "busy"):
            raise ValueError("unsupported retry decision")
        status = result.status
    else:
        inspection = result.inspection
        if not isinstance(inspection, QueuedSFTPInspection):
            raise TypeError("QueuedSFTPInspection required")
        if (inspection.job_id, inspection.customer_id, inspection.project_id) != (
            job.job_id, job.customer_id, job.project_id
        ):
            raise PermissionError("inspection identity mismatch")
        status = "ready" if inspection.directory_exists is True else "missing_directory"
        if type(inspection.directory_exists) is not bool:
            raise TypeError("directory_exists must be boolean")
    return RetryInspectionSummary(job.job_id, job.customer_id, job.project_id, status)
