"""Explicit opt-in retry claim facade; never performs an SFTP request."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SFTPPreflightRetryClaim:
    decision: str
    token: str | None


class SFTPPreflightRetryClaimService:
    def __init__(self, leases):
        self._leases = leases

    def claim(self, job_id, customer_id, project_id, worker_id, *, now=None, lease_seconds=60):
        decision, token = self._leases.claim(
            job_id, customer_id, project_id, worker_id,
            now=now, lease_seconds=lease_seconds,
        )
        return SFTPPreflightRetryClaim(decision, token)

    def release(self, job_id, customer_id, project_id, worker_id, token):
        return self._leases.release(job_id, customer_id, project_id, worker_id, token)
