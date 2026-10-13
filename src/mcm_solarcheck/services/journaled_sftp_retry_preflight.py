"""Explicit read-only preflight retry with atomic outcome recording."""
from __future__ import annotations

from mcm_solarcheck.services.queued_job_dispatcher import PendingProjectJob
from mcm_solarcheck.services.sftp_preflight_retry_work_guard import RetryWorkIdentity
from mcm_solarcheck.services.sftp_retry_inspection_summary import summarize_retry_inspection


class JournaledSFTPRetryPreflight:
    def __init__(self, claims, guarded_preflight, journal):
        self.claims = claims
        self.guarded_preflight = guarded_preflight
        self.journal = journal

    def inspect_once(self, job: PendingProjectJob, worker_id: str, *, now=None, lease_seconds=60):
        if not isinstance(job, PendingProjectJob):
            raise TypeError("PendingProjectJob required")
        claim = self.claims.claim(
            job.job_id, job.customer_id, job.project_id, worker_id,
            now=now, lease_seconds=lease_seconds
        )
        if claim.decision != "claimed":
            return claim.decision
        identity = RetryWorkIdentity(job.job_id, job.customer_id, job.project_id, worker_id, claim.token)
        try:
            inspection = self.guarded_preflight.inspect(job, identity, now=now)
            from mcm_solarcheck.services.explicit_queued_sftp_preflight_retry import RetryPreflightResult
            summary = summarize_retry_inspection(job, RetryPreflightResult("inspected", inspection))
            return self.journal.record(identity, summary, now=now)
        finally:
            self.claims.release(
                identity.job_id, identity.customer_id, identity.project_id,
                identity.worker_id, identity.token
            )
