"""Compose opt-in journaled retry inspection; no scheduler or network connection."""
from __future__ import annotations

from mcm_solarcheck.infrastructure.sqlite_sftp_preflight_retry_leases import SQLiteSFTPPreflightRetryLeases
from mcm_solarcheck.infrastructure.sqlite_sftp_retry_outcome_journal import SQLiteSFTPRetryOutcomeJournal
from mcm_solarcheck.services.sftp_preflight_retry_claim_service import SFTPPreflightRetryClaimService
from mcm_solarcheck.services.sftp_preflight_retry_work_guard import SFTPPreflightRetryWorkGuard
from mcm_solarcheck.services.guarded_queued_sftp_preflight_retry import GuardedQueuedSFTPPreflightRetry
from mcm_solarcheck.services.journaled_sftp_retry_preflight import JournaledSFTPRetryPreflight


def build_journaled_sftp_retry_preflight(database, preflight):
    leases = SQLiteSFTPPreflightRetryLeases(database)
    return JournaledSFTPRetryPreflight(
        SFTPPreflightRetryClaimService(leases),
        GuardedQueuedSFTPPreflightRetry(SFTPPreflightRetryWorkGuard(leases), preflight),
        SQLiteSFTPRetryOutcomeJournal(database),
    )
