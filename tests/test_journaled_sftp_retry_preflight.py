from datetime import datetime, timedelta, timezone

from mcm_solarcheck.infrastructure.sqlite_sftp_preflight_retries import SQLiteSFTPPreflightRetries
from mcm_solarcheck.infrastructure.sqlite_sftp_preflight_retry_leases import SQLiteSFTPPreflightRetryLeases
from mcm_solarcheck.infrastructure.sqlite_sftp_retry_outcome_journal import SQLiteSFTPRetryOutcomeJournal
from mcm_solarcheck.services.queued_job_dispatcher import PendingProjectJob
from mcm_solarcheck.services.queued_sftp_preflight import QueuedSFTPInspection
from mcm_solarcheck.services.sftp_preflight_retry_work_guard import RetryWorkIdentity
from mcm_solarcheck.services.sftp_retry_inspection_summary import RetryInspectionSummary
from mcm_solarcheck.services.journaled_sftp_retry_composition import build_journaled_sftp_retry_preflight


def test_journaled_preflight_records_and_releases(tmp_path):
    path = tmp_path / "retry.db"
    now = datetime(2026, 10, 1, tzinfo=timezone.utc)
    SQLiteSFTPPreflightRetries(path).record_failure("j", "c", "p", "network", now=now)

    class Preflight:
        def inspect(self, job):
            return QueuedSFTPInspection(job.job_id, job.customer_id, job.project_id, True)

    runner = build_journaled_sftp_retry_preflight(path, Preflight())
    job = PendingProjectJob(customer_id="c", project_id="p", job_id="j")
    assert runner.inspect_once(job, "worker", now=now + timedelta(seconds=30)) == "recorded"
    assert len(SQLiteSFTPRetryOutcomeJournal(path).history("j", "c", "p")) == 1
    assert SQLiteSFTPRetryOutcomeJournal(path).history("j", "other", "p") == []
    assert SQLiteSFTPPreflightRetryLeases(path).claim(
        "j", "c", "p", "second", now=now + timedelta(seconds=30)
    )[0] == "claimed"


def test_stale_token_cannot_record_or_overwrite(tmp_path):
    path = tmp_path / "retry.db"
    now = datetime(2026, 10, 1, tzinfo=timezone.utc)
    SQLiteSFTPPreflightRetries(path).record_failure("j", "c", "p", "network", now=now)
    leases = SQLiteSFTPPreflightRetryLeases(path)
    journal = SQLiteSFTPRetryOutcomeJournal(path)
    ready = now + timedelta(seconds=30)
    decision, old = leases.claim("j", "c", "p", "old", now=ready, lease_seconds=10)
    assert decision == "claimed"
    decision, new = leases.claim("j", "c", "p", "new", now=ready + timedelta(seconds=10))
    assert decision == "claimed"
    summary = RetryInspectionSummary("j", "c", "p", "ready")
    assert journal.record(RetryWorkIdentity("j", "c", "p", "old", old), summary, now=ready + timedelta(seconds=10)) == "lease_lost"
    assert journal.record(RetryWorkIdentity("j", "c", "p", "new", new), summary, now=ready + timedelta(seconds=10)) == "recorded"
    assert journal.record(RetryWorkIdentity("j", "c", "p", "new", new), summary, now=ready + timedelta(seconds=10)) == "already_recorded"
    assert journal.record(RetryWorkIdentity("j", "c", "p", "new", new), RetryInspectionSummary("j", "c", "p", "missing_directory"), now=ready + timedelta(seconds=10)) == "conflict"
    assert len(journal.history("j", "c", "p")) == 1
