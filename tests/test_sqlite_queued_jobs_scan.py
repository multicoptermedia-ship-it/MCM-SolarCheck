"""Queued SQLite jobs survive store reinitialization and retain FIFO ordering."""
from mcm_solarcheck.infrastructure.sqlite_compute_jobs import SQLiteComputeJobStore
from mcm_solarcheck.services.compute_jobs import ComputeJob, ComputeJobStatus


def test_queued_jobs_survive_reopen_and_are_fifo(tmp_path):
    db = tmp_path / "jobs.sqlite"
    store = SQLiteComputeJobStore(db)
    for job_id in ("first", "second", "third"):
        store.create(ComputeJob(job_id, "customer-" + job_id, "project-" + job_id, ComputeJobStatus.QUEUED))
    reopened = SQLiteComputeJobStore(db)
    assert [job.job_id for job in reopened.queued_jobs(limit=2)] == ["first", "second"]
    assert [job.user_id for job in reopened.queued_jobs()] == [
        "customer-first", "customer-second", "customer-third"
    ]


def test_running_jobs_are_not_in_queued_scan(tmp_path):
    store = SQLiteComputeJobStore(tmp_path / "jobs.sqlite")
    store.create(ComputeJob("j1", "u1", "p1", ComputeJobStatus.QUEUED))
    store.create(ComputeJob("j2", "u2", "p2", ComputeJobStatus.RUNNING))
    assert [job.job_id for job in store.queued_jobs()] == ["j1"]
