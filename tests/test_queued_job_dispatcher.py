"""Dispatch pending jobs with authoritative capacity and owner scope."""
from concurrent.futures import Future
from types import SimpleNamespace

import pytest

from mcm_solarcheck.services.compute_jobs import ComputeJobStatus
from mcm_solarcheck.services.queued_job_dispatcher import PendingProjectJob, QueuedJobDispatcher


class Jobs:
    def __init__(self):
        self.running = 0
        self.owner = {"a": ("alice", "pa"), "b": ("bob", "pb"), "c": ("carol", "pc")}
        self.status = {key: ComputeJobStatus.QUEUED for key in self.owner}

    def get(self, job_id, *, user_id, project_id):
        if self.owner[job_id] != (user_id, project_id):
            raise PermissionError("wrong owner")
        return SimpleNamespace(status=self.status[job_id])

    def start(self, job_id, *, user_id, project_id, capacity):
        self.get(job_id, user_id=user_id, project_id=project_id)
        if self.running < capacity.max_parallel_jobs:
            self.running += 1
            self.status[job_id] = ComputeJobStatus.RUNNING
        return SimpleNamespace(status=self.status[job_id])


class Workers:
    def __init__(self):
        self.submitted = []

    def submit(self, *, customer_id, project_id, job_id):
        self.submitted.append((customer_id, project_id, job_id))
        return Future()


def test_two_dispatch_and_third_stays_queued():
    jobs, workers = Jobs(), Workers()
    dispatcher = QueuedJobDispatcher(jobs, workers)
    items = [PendingProjectJob(u, p, j) for u, p, j in (("alice", "pa", "a"), ("bob", "pb", "b"), ("carol", "pc", "c"))]
    result = dispatcher.dispatch(items)
    assert set(result) == {"a", "b"}
    assert jobs.status["c"] is ComputeJobStatus.QUEUED
    assert len(workers.submitted) == 2
    assert dispatcher.dispatch(items) == {}


def test_owner_mismatch_rejected_before_admission():
    jobs, workers = Jobs(), Workers()
    with pytest.raises(PermissionError):
        QueuedJobDispatcher(jobs, workers).dispatch([PendingProjectJob("alice", "pb", "b")])
    assert jobs.running == 0
    assert workers.submitted == []
