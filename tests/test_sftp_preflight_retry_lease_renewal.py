from datetime import datetime, timedelta, timezone

import pytest

from mcm_solarcheck.infrastructure.sqlite_sftp_preflight_retries import SQLiteSFTPPreflightRetries
from mcm_solarcheck.infrastructure.sqlite_sftp_preflight_retry_leases import SQLiteSFTPPreflightRetryLeases
from mcm_solarcheck.services.sftp_preflight_retry_claim_service import SFTPPreflightRetryClaimService
from mcm_solarcheck.services.sftp_preflight_retry_lease_inspector import SFTPPreflightRetryLeaseInspector


def setup_lease(tmp_path):
    path = tmp_path / "shared.sqlite"
    at = datetime(2026, 10, 1, tzinfo=timezone.utc)
    SQLiteSFTPPreflightRetries(path).record_failure("job", "customer", "project", "timeout", now=at)
    leases = SQLiteSFTPPreflightRetryLeases(path)
    service = SFTPPreflightRetryClaimService(leases)
    start = at + timedelta(seconds=30)
    claim = service.claim("job", "customer", "project", "worker1", now=start, lease_seconds=20)
    assert claim.decision == "claimed"
    return service, SFTPPreflightRetryLeaseInspector(leases), start, claim.token


def test_live_renewal_extends_expiry_and_rejects_wrong_token(tmp_path):
    service, inspector, start, token = setup_lease(tmp_path)
    assert inspector.inspect("job", "customer", "project", now=start) == "active"
    assert not service.renew("job", "customer", "project", "worker1", "wrong", now=start)
    assert not service.renew("job", "customer", "project", "worker2", token, now=start)
    assert service.renew("job", "customer", "project", "worker1", token, now=start + timedelta(seconds=10), lease_seconds=30)
    assert inspector.inspect("job", "customer", "project", now=start + timedelta(seconds=25)) == "active"
    assert inspector.inspect("job", "customer", "project", now=start + timedelta(seconds=40)) == "expired"


def test_expired_or_replaced_token_cannot_renew(tmp_path):
    service, _, start, token = setup_lease(tmp_path)
    assert not service.renew("job", "customer", "project", "worker1", token, now=start + timedelta(seconds=20))
    replacement = service.claim("job", "customer", "project", "worker2", now=start + timedelta(seconds=20))
    assert replacement.decision == "claimed"
    assert not service.renew("job", "customer", "project", "worker1", token, now=start + timedelta(seconds=21))
    assert service.renew("job", "customer", "project", "worker2", replacement.token, now=start + timedelta(seconds=21))


def test_owner_isolation_and_invalid_clock(tmp_path):
    service, inspector, start, token = setup_lease(tmp_path)
    with pytest.raises(PermissionError):
        inspector.inspect("job", "other", "project", now=start)
    with pytest.raises(ValueError):
        service.renew("job", "customer", "project", "worker1", token, now=datetime(2026, 10, 1))
    assert inspector.inspect("unknown", "customer", "project", now=start) == "not_leased"
