"""Opt-in guarded read-only SFTP preflight for a previously claimed retry lease."""
from __future__ import annotations

from mcm_solarcheck.services.queued_job_dispatcher import PendingProjectJob
from mcm_solarcheck.services.sftp_preflight_retry_work_guard import RetryWorkIdentity


class GuardedQueuedSFTPPreflightRetry:
    def __init__(self, guard, preflight):
        self.guard = guard
        self.preflight = preflight

    def inspect(self, job: PendingProjectJob, identity: RetryWorkIdentity, *, now=None):
        if not isinstance(job, PendingProjectJob):
            raise TypeError("PendingProjectJob required")
        if not isinstance(identity, RetryWorkIdentity):
            raise TypeError("RetryWorkIdentity required")
        if (job.job_id, job.customer_id, job.project_id) != (
            identity.job_id, identity.customer_id, identity.project_id
        ):
            raise PermissionError("retry identity does not match queued job")
        self.guard.require_live(identity, now=now)
        return self.preflight.inspect(job)
