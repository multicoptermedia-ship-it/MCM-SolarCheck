from datetime import datetime, timedelta, timezone

import pytest

from mcm_solarcheck.infrastructure.sqlite_sftp_preflight_retries import SQLiteSFTPPreflightRetries
from mcm_solarcheck.infrastructure.sqlite_sftp_preflight_retry_leases import SQLiteSFTPPreflightRetryLeases
from mcm_solarcheck.services.queued_job_dispatcher import PendingProjectJob
from mcm_solarcheck.services.guarded_queued_sftp_preflight_retry import GuardedQueuedSFTPPreflightRetry
from mcm_solarcheck.services.sftp_preflight_retry_work_guard import (
    LostRetryLeaseError, RetryWorkIdentity, SFTPPreflightRetryWorkGuard,
)


def test_replaced_lease_discards_completed_preflight(tmp_path):
    path = tmp_path / "retry.sqlite"
    start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    SQLiteSFTPPreflightRetries(path).record_failure("j", "c", "p", "network", now=start)
    leases = SQLiteSFTPPreflightRetryLeases(path)
    ready = start + timedelta(seconds=30)
    decision, token = leases.claim("j", "c", "p", "worker1", now=ready, lease_seconds=10)
    assert decision == "claimed"

    class ReplacingPreflight:
        def inspect(self, job):
            replacement, _ = leases.claim(
                "j", "c", "p", "worker2", now=ready + timedelta(seconds=10)
            )
            assert replacement == "claimed"
            return "should_not_be_accepted"

    guarded = GuardedQueuedSFTPPreflightRetry(
        SFTPPreflightRetryWorkGuard(leases), ReplacingPreflight()
    )
    with pytest.raises(LostRetryLeaseError):
        guarded.inspect(
            PendingProjectJob(customer_id="c", project_id="p", job_id="j"),
            RetryWorkIdentity("j", "c", "p", "worker1", token),
            now=ready,
        )


def test_preflight_identity_mismatch_prevents_call():
    class NoCall:
        def inspect(self, job):
            raise AssertionError("must not run")

    guarded = GuardedQueuedSFTPPreflightRetry(None, NoCall())
    with pytest.raises(PermissionError):
        guarded.inspect(
            PendingProjectJob(customer_id="c", project_id="p", job_id="j"),
            RetryWorkIdentity("j", "c", "different", "worker", "token"),
        )
