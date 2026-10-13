"""Explicit guarded execution of local preflight steps, without automatic retries."""
from __future__ import annotations

from mcm_solarcheck.services.sftp_preflight_retry_work_guard import RetryWorkIdentity


class GuardedSFTPPreflightRetryStep:
    def __init__(self, guard):
        self.guard = guard

    def run(self, identity: RetryWorkIdentity, operation, *, now=None):
        """Check the lease before calling an injected local operation.

        This does not fence remote writes or guarantee the lease stays live
        for the entire operation.
        """
        if not callable(operation):
            raise TypeError("operation must be callable")
        self.guard.require_live(identity, now=now)
        return operation()
