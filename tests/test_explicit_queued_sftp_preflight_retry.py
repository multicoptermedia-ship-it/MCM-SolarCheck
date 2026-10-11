from datetime import datetime, timedelta, timezone

import pytest

from mcm_solarcheck.infrastructure.sqlite_sftp_preflight_retries import SQLiteSFTPPreflightRetries
from mcm_solarcheck.infrastructure.sqlite_sftp_preflight_retry_leases import SQLiteSFTPPreflightRetryLeases
from mcm_solarcheck.services.queued_job_dispatcher import PendingProjectJob
from mcm_solarcheck.services.explicit_sftp_retry_composition import build_explicit_queued_sftp_preflight_retry
from mcm_solarcheck.services.sftp_preflight_retry_work_guard import RetryWorkIdentity
from mcm_solarcheck.services.guarded_queued_sftp_preflight_retry import GuardedQueuedSFTPPreflightRetry


class FakePreflight:
    def __init__(self, error=None):
        self.calls = []
        self.error = error

    def inspect(self, job):
        self.calls.append(job.job_id)
        if self.error:
            raise self.error
        return "directory_checked"


def setup(tmp_path, preflight):
    path = tmp_path / "retry.sqlite"
    now = datetime(2026, 10, 1, tzinfo=timezone.utc)
    SQLiteSFTPPreflightRetries(path).record_failure("job", "customer", "project", "network", now=now)
    return path, now + timedelta(seconds=30), build_explicit_queued_sftp_preflight_retry(path, preflight)


def test_explicit_retry_inspects_once_and_releases(tmp_path):
    preflight = FakePreflight()
    path, ready, runner = setup(tmp_path, preflight)
    job = PendingProjectJob("job", "customer", "project")
    result = runner.inspect_once(job, "worker", now=ready)
    assert result.status == "inspected"
    assert result.inspection == "directory_checked"
    assert preflight.calls == ["job"]
    assert SQLiteSFTPPreflightRetryLeases(path).claim(
        "job", "customer", "project", "another", now=ready
    )[0] == "claimed"


def test_error_releases_lease_without_automatic_retry(tmp_path):
    preflight = FakePreflight(RuntimeError("read failed"))
    path, ready, runner = setup(tmp_path, preflight)
    job = PendingProjectJob("job", "customer", "project")
    with pytest.raises(RuntimeError, match="read failed"):
        runner.inspect_once(job, "worker", now=ready)
    assert preflight.calls == ["job"]
    assert SQLiteSFTPPreflightRetryLeases(path).claim(
        "job", "customer", "project", "another", now=ready
    )[0] == "claimed"


def test_waiting_retry_does_not_inspect(tmp_path):
    preflight = FakePreflight()
    _, ready, runner = setup(tmp_path, preflight)
    job = PendingProjectJob("job", "customer", "project")
    result = runner.inspect_once(job, "worker", now=ready - timedelta(seconds=1))
    assert result.status == "wait"
    assert preflight.calls == []


def test_guard_rejects_cross_project_identity(tmp_path):
    preflight = FakePreflight()
    path, ready, _ = setup(tmp_path, preflight)
    guarded = GuardedQueuedSFTPPreflightRetry(
        __import__("mcm_solarcheck.services.sftp_preflight_retry_work_guard", fromlist=["SFTPPreflightRetryWorkGuard"]).SFTPPreflightRetryWorkGuard(
            SQLiteSFTPPreflightRetryLeases(path)
        ), preflight
    )
    with pytest.raises(PermissionError):
        guarded.inspect(
            PendingProjectJob("job", "customer", "project"),
            RetryWorkIdentity("job", "customer", "other", "worker", "token"),
            now=ready,
        )
    assert preflight.calls == []
