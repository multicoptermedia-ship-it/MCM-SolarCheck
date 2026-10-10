from datetime import datetime, timedelta, timezone

import pytest

from mcm_solarcheck.infrastructure.sqlite_sftp_preflight_retries import SQLiteSFTPPreflightRetries
from mcm_solarcheck.services.sftp_preflight_retry_readiness import SFTPPreflightRetryReadiness
from mcm_solarcheck.services.sftp_preflight_retry_recorder import SFTPPreflightRetryRecorder
from mcm_solarcheck.services.sftp_preflight_outcomes import SFTPPreflightOutcome


def test_retry_counter_survives_reopening_and_obeys_deadlines(tmp_path):
    path = tmp_path / "retries.sqlite"
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    ledger = SQLiteSFTPPreflightRetries(path)
    recorder = SFTPPreflightRetryRecorder(ledger)
    outcome = SFTPPreflightOutcome("j1", "c1", "p1", "failed", "timeout")
    assert recorder.record(outcome, now=now)[0:2] == ("waiting", 1)
    reopened = SQLiteSFTPPreflightRetries(path)
    readiness = SFTPPreflightRetryReadiness(reopened)
    assert readiness.assess("j1", "c1", "p1", now=now) == "wait"
    assert readiness.assess("j1", "c1", "p1", now=now + timedelta(seconds=30)) == "eligible"
    assert recorder.record(outcome, now=now + timedelta(seconds=30))[0:2] == ("waiting", 2)
    assert recorder.record(outcome, now=now + timedelta(seconds=90))[0:2] == ("exhausted", 3)
    assert readiness.assess("j1", "c1", "p1", now=now + timedelta(days=1)) == "manual_review"
    assert recorder.record(outcome, now=now + timedelta(days=2))[0:2] == ("exhausted", 3)


def test_retry_identity_is_owner_scoped(tmp_path):
    ledger = SQLiteSFTPPreflightRetries(tmp_path / "retry.sqlite")
    ledger.record_failure("job", "owner", "project", "network")
    with pytest.raises(PermissionError):
        ledger.inspect("job", "another", "project")
    with pytest.raises(PermissionError):
        ledger.record_failure("job", "another", "project", "timeout")


def test_nontransient_outcomes_are_not_persisted(tmp_path):
    ledger = SQLiteSFTPPreflightRetries(tmp_path / "retry.sqlite")
    recorder = SFTPPreflightRetryRecorder(ledger)
    outcome = SFTPPreflightOutcome("j", "c", "p", "failed", "authentication")
    assert recorder.record(outcome) == ("not_retryable", 0, None)
    assert ledger.inspect("j", "c", "p") is None


def test_naive_clock_rejected(tmp_path):
    ledger = SQLiteSFTPPreflightRetries(tmp_path / "retry.sqlite")
    with pytest.raises(ValueError):
        ledger.record_failure("j", "c", "p", "network", now=datetime(2026, 1, 1))
