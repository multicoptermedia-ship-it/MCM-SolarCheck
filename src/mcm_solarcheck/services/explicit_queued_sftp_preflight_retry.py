"""Explicit single-job retry lifecycle, without scheduling or automatic execution."""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.sftp_preflight_retry_work_guard import RetryWorkIdentity


@dataclass(frozen=True)
class RetryPreflightResult:
    status: str
    inspection: object | None = None


class ExplicitQueuedSFTPPreflightRetry:
    def __init__(self, claims, guarded_preflight):
        self.claims = claims
        self.guarded_preflight = guarded_preflight

    def inspect_once(self, job, worker_id, *, now=None, lease_seconds=60):
        claim = self.claims.claim(
            job.job_id, job.customer_id, job.project_id, worker_id,
            now=now, lease_seconds=lease_seconds,
        )
        if claim.decision != "claimed":
            return RetryPreflightResult(claim.decision)
        identity = RetryWorkIdentity(
            job.job_id, job.customer_id, job.project_id, worker_id, claim.token
        )
        try:
            inspection = self.guarded_preflight.inspect(job, identity, now=now)
            return RetryPreflightResult("inspected", inspection)
        finally:
            self.claims.release(
                identity.job_id, identity.customer_id, identity.project_id,
                identity.worker_id, identity.token,
            )
