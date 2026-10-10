"""Sanitized per-job SFTP preflight outcome without raw exception messages."""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.infrastructure.sftp_failure_classifier import classify_sftp_failure


@dataclass(frozen=True)
class SFTPPreflightOutcome:
    job_id: str
    customer_id: str
    project_id: str
    status: str
    failure_category: str | None = None


def classify_preflight_outcome(job, inspection=None, error=None):
    if error is not None:
        return SFTPPreflightOutcome(
            job.job_id, job.customer_id, job.project_id,
            "failed", classify_sftp_failure(error),
        )
    if inspection is None:
        raise ValueError("inspection or error required")
    return SFTPPreflightOutcome(
        job.job_id, job.customer_id, job.project_id,
        "ready" if inspection.directory_exists else "missing_directory",
    )
