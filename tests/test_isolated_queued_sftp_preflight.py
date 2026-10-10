from types import SimpleNamespace

from mcm_solarcheck.services.isolated_queued_sftp_preflight_batch import IsolatedQueuedSFTPPreflightBatch
from mcm_solarcheck.services.sftp_preflight_retry_policy import advise_sftp_preflight_retry


class Store:
    def queued_jobs(self, limit):
        assert limit == 5
        return [
            SimpleNamespace(user_id="a", project_id="p1", job_id="j1"),
            SimpleNamespace(user_id="b", project_id="p2", job_id="j2"),
            SimpleNamespace(user_id="c", project_id="p3", job_id="j3"),
        ]


class Preflight:
    def inspect(self, job):
        if job.job_id == "j1":
            raise TimeoutError("secret: connection timed out")
        if job.job_id == "j2":
            return SimpleNamespace(directory_exists=False)
        return SimpleNamespace(directory_exists=True)


def test_failure_does_not_block_other_customers_or_leak_exception():
    results = IsolatedQueuedSFTPPreflightBatch(Store(), Preflight(), batch_size=5).tick()
    assert [(x.job_id, x.status) for x in results] == [
        ("j1", "failed"), ("j2", "missing_directory"), ("j3", "ready")
    ]
    assert results[0].failure_category == "timeout"
    assert "secret" not in repr(results)
    assert advise_sftp_preflight_retry(results[0]).decision == "retry_with_backoff"
    assert advise_sftp_preflight_retry(results[0]).max_attempts == 3
    assert advise_sftp_preflight_retry(results[1]).decision == "manual_review"
    assert advise_sftp_preflight_retry(results[2]).decision == "no_retry_needed"


def test_unknown_errors_are_not_retried():
    class Broken:
        def inspect(self, job):
            raise RuntimeError("unexpected")

    outcomes = IsolatedQueuedSFTPPreflightBatch(Store(), Broken(), batch_size=5).tick()
    assert all(advise_sftp_preflight_retry(x).decision == "manual_review" for x in outcomes)
