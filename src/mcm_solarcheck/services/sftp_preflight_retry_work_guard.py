"""Fail-closed preflight retry work checkpoint; no SFTP operations are executed."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryWorkIdentity:
    job_id: str
    customer_id: str
    project_id: str
    worker_id: str
    token: str


class LostRetryLeaseError(RuntimeError):
    """The caller must stop initiating new work."""


class SFTPPreflightRetryWorkGuard:
    def __init__(self, leases):
        self.leases = leases

    def require_live(self, identity: RetryWorkIdentity, *, now=None):
        if not isinstance(identity, RetryWorkIdentity):
            raise TypeError("RetryWorkIdentity required")
        if not self.leases.owns_live_lease(
            identity.job_id, identity.customer_id, identity.project_id,
            identity.worker_id, identity.token, now=now,
        ):
            raise LostRetryLeaseError("retry lease unavailable")
        return True
