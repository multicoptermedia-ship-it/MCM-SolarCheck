from datetime import datetime, timedelta, timezone

import pytest

from mcm_solarcheck.infrastructure.sqlite_sftp_preflight_retries import SQLiteSFTPPreflightRetries
from mcm_solarcheck.infrastructure.sqlite_sftp_preflight_retry_leases import SQLiteSFTPPreflightRetryLeases
from mcm_solarcheck.services.sftp_preflight_retry_work_guard import (
    RetryWorkIdentity, LostRetryLeaseError, SFTPPreflightRetryWorkGuard,
)
from mcm_solarcheck.services.guarded_sftp_preflight_retry_step import GuardedSFTPPreflightRetryStep


def setup(tmp_path):
    path = tmp_path / "retry.sqlite"
    at = datetime(2026, 10, 1, tzinfo=timezone.utc)
    SQLiteSFTPPreflightRetries(path).record_failure("j", "c", "p", "network", now=at)
    leases = SQLiteSFTPPreflightRetryLeases(path)
    start = at + timedelta(seconds=30)
    decision, token = leases.claim("j", "c", "p", "w1", now=start, lease_seconds=10)
    assert decision == "claimed"
    return leases, start, RetryWorkIdentity("j", "c", "p", "w1", token)


def test_guard_runs_only_for_live_owner(tmp_path):
    leases, start, identity = setup(tmp_path)
    step = GuardedSFTPPreflightRetryStep(SFTPPreflightRetryWorkGuard(leases))
    called = []
    assert step.run(identity, lambda: called.append("ok"), now=start) is None
    assert called == ["ok"]
    with pytest.raises(LostRetryLeaseError):
        step.run(identity, lambda: called.append("bad"), now=start + timedelta(seconds=10))
    assert called == ["ok"]


def test_replaced_token_cannot_start_new_step(tmp_path):
    leases, start, identity = setup(tmp_path)
    assert leases.claim("j", "c", "p", "w2", now=start + timedelta(seconds=10))[0] == "claimed"
    guard = SFTPPreflightRetryWorkGuard(leases)
    with pytest.raises(LostRetryLeaseError):
        guard.require_live(identity, now=start + timedelta(seconds=11))


def test_owner_and_invalid_identity_fail_closed(tmp_path):
    leases, start, identity = setup(tmp_path)
    guard = SFTPPreflightRetryWorkGuard(leases)
    with pytest.raises(LostRetryLeaseError):
        guard.require_live(RetryWorkIdentity("j", "other", "p", "w1", identity.token), now=start)
    with pytest.raises(TypeError):
        guard.require_live(None, now=start)


def test_exhaustion_revokes_work_eligibility(tmp_path):
    leases, start, identity = setup(tmp_path)
    ledger = SQLiteSFTPPreflightRetries(leases.database)
    ledger.record_failure("j", "c", "p", "network", now=start)
    ledger.record_failure("j", "c", "p", "network", now=start + timedelta(seconds=60))
    with pytest.raises(LostRetryLeaseError):
        SFTPPreflightRetryWorkGuard(leases).require_live(identity, now=start + timedelta(seconds=1))
