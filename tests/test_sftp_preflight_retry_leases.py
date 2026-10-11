from datetime import datetime, timedelta, timezone

import pytest

from mcm_solarcheck.infrastructure.sqlite_sftp_preflight_retries import SQLiteSFTPPreflightRetries
from mcm_solarcheck.infrastructure.sqlite_sftp_preflight_retry_leases import SQLiteSFTPPreflightRetryLeases
from mcm_solarcheck.services.sftp_preflight_retry_claim_service import SFTPPreflightRetryClaimService


def setup(tmp_path):
    path = tmp_path / "retries.sqlite"
    ledger = SQLiteSFTPPreflightRetries(path)
    leases = SQLiteSFTPPreflightRetryLeases(path)
    instant = datetime(2026, 10, 1, tzinfo=timezone.utc)
    ledger.record_failure("j", "c", "p", "network", now=instant)
    return path, instant, SFTPPreflightRetryClaimService(leases)


def test_only_one_active_claim_and_release_requires_token(tmp_path):
    path, now, service = setup(tmp_path)
    ready = now + timedelta(seconds=30)
    first = service.claim("j", "c", "p", "worker1", now=ready)
    assert first.decision == "claimed"
    other = SFTPPreflightRetryClaimService(SQLiteSFTPPreflightRetryLeases(path))
    assert other.claim("j", "c", "p", "worker2", now=ready).decision == "busy"
    assert not other.release("j", "c", "p", "worker2", first.token)
    assert service.release("j", "c", "p", "worker1", first.token)
    assert other.claim("j", "c", "p", "worker2", now=ready).decision == "claimed"


def test_expiry_changes_token_and_old_owner_cannot_release(tmp_path):
    _, now, service = setup(tmp_path)
    ready = now + timedelta(seconds=30)
    first = service.claim("j", "c", "p", "worker1", now=ready, lease_seconds=10)
    second = service.claim("j", "c", "p", "worker2", now=ready + timedelta(seconds=10))
    assert second.decision == "claimed"
    assert second.token != first.token
    assert not service.release("j", "c", "p", "worker1", first.token)


def test_wait_and_owner_rejection(tmp_path):
    _, now, service = setup(tmp_path)
    assert service.claim("j", "c", "p", "worker1", now=now).decision == "wait"
    with pytest.raises(PermissionError):
        service.claim("j", "other", "p", "worker1", now=now + timedelta(seconds=30))


def test_exhausted_retry_not_claimed(tmp_path):
    path, now, service = setup(tmp_path)
    ledger = SQLiteSFTPPreflightRetries(path)
    ledger.record_failure("j", "c", "p", "network", now=now + timedelta(seconds=30))
    ledger.record_failure("j", "c", "p", "network", now=now + timedelta(seconds=90))
    assert service.claim("j", "c", "p", "worker", now=now + timedelta(days=1)).decision == "manual_review"
