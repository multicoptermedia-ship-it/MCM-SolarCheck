"""Opt-in wiring for one guarded queued SFTP preflight retry.

Does not start workers, schedule retries, or configure any real SFTP connection.
"""
from __future__ import annotations

from mcm_solarcheck.infrastructure.sqlite_sftp_preflight_retry_leases import SQLiteSFTPPreflightRetryLeases
from mcm_solarcheck.services.sftp_preflight_retry_claim_service import SFTPPreflightRetryClaimService
from mcm_solarcheck.services.sftp_preflight_retry_work_guard import SFTPPreflightRetryWorkGuard
from mcm_solarcheck.services.guarded_queued_sftp_preflight_retry import GuardedQueuedSFTPPreflightRetry
from mcm_solarcheck.services.explicit_queued_sftp_preflight_retry import ExplicitQueuedSFTPPreflightRetry


def build_explicit_queued_sftp_preflight_retry(database, preflight):
    leases = SQLiteSFTPPreflightRetryLeases(database)
    claims = SFTPPreflightRetryClaimService(leases)
    guard = SFTPPreflightRetryWorkGuard(leases)
    return ExplicitQueuedSFTPPreflightRetry(
        claims, GuardedQueuedSFTPPreflightRetry(guard, preflight)
    )
