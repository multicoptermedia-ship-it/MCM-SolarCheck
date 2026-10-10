"""Duplicate queue entries must not start the same job twice."""
from concurrent.futures import Future
from types import SimpleNamespace

from mcm_solarcheck.services.compute_jobs import ComputeJobStatus
from mcm_solarcheck.services.queued_job_dispatcher import PendingProjectJob, QueuedJobDispatcher


class Jobs:
    def __init__(self):
        self.starts = 0

    def get(self, job_id, *, user_id, project_id):
        return SimpleNamespace(status=ComputeJobStatus.QUEUED)

    def start(self, job_id, *, user_id, project_id, capacity):
        self.starts += 1
        return SimpleNamespace(status=ComputeJobStatus.RUNNING)


class Workers:
    def __init__(self):
        self.calls = 0

    def submit(self, **kwargs):
        self.calls += 1
        return Future()


def test_duplicate_pending_entry_only_scheduled_once():
    jobs, workers = Jobs(), Workers()
    item = PendingProjectJob("alice", "pa", "a")
    result = QueuedJobDispatcher(jobs, workers).dispatch([item, item])
    assert list(result) == ["a"]
    assert jobs.starts == workers.calls == 1
