from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from mcm_solarcheck.infrastructure.sqlite_sftp_preflight_retries import SQLiteSFTPPreflightRetries
from mcm_solarcheck.infrastructure.sqlite_sftp_preflight_retry_leases import SQLiteSFTPPreflightRetryLeases


def test_competing_workers_cannot_claim_same_retry(tmp_path):
    path = tmp_path / "shared.sqlite"
    ledger = SQLiteSFTPPreflightRetries(path)
    at = datetime(2026, 10, 1, tzinfo=timezone.utc)
    ledger.record_failure("job", "customer", "project", "timeout", now=at)
    ready = at + timedelta(seconds=30)

    def claim(worker):
        return SQLiteSFTPPreflightRetryLeases(path).claim(
            "job", "customer", "project", worker, now=ready
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(claim, [f"worker{i}" for i in range(8)]))
    assert [decision for decision, _ in outcomes].count("claimed") == 1
    assert [decision for decision, _ in outcomes].count("busy") == 7


def test_unrecorded_and_invalid_lease_duration(tmp_path):
    leases = SQLiteSFTPPreflightRetryLeases(tmp_path / "shared.sqlite")
    # A missing retry table is a configuration error, not a permission to claim.
    with pytest.raises(Exception):
        leases.claim("j", "c", "p", "worker")
    with pytest.raises(ValueError):
        leases.claim("j", "c", "p", "worker", lease_seconds=0)
