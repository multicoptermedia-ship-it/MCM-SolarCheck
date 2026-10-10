"""Real overlapping worker tasks with owner checks and bounded admission."""
from threading import Event
from types import SimpleNamespace

import pytest

from mcm_solarcheck.services.compute_jobs import ComputeJobStatus
from mcm_solarcheck.services.parallel_processing_workers import ParallelProjectWorkers


class Jobs:
    def get(self, job_id, *, user_id, project_id):
        if (job_id, user_id, project_id) not in (
            ("a", "alice", "pa"), ("b", "bob", "pb"), ("c", "carol", "pc")
        ):
            raise PermissionError("wrong owner")
        return SimpleNamespace(status=ComputeJobStatus.RUNNING if job_id != "c" else ComputeJobStatus.QUEUED)


class Processing:
    def __init__(self):
        self.started = Event()
        self.second = Event()
        self.release = Event()
        self.requests = []

    def process(self, request):
        self.requests.append(request)
        if len(self.requests) == 1:
            self.started.set()
        else:
            self.second.set()
        assert self.release.wait(5)
        return request.project_id


def test_two_customers_actually_overlap_and_third_queued():
    processing = Processing()
    workers = ParallelProjectWorkers(Jobs(), processing, max_workers=2)
    try:
        first = workers.submit(customer_id="alice", project_id="pa", job_id="a")
        assert processing.started.wait(3)
        second = workers.submit(customer_id="bob", project_id="pb", job_id="b")
        assert processing.second.wait(3)
        with pytest.raises(ValueError):
            workers.submit(customer_id="carol", project_id="pc", job_id="c")
        with pytest.raises(PermissionError):
            workers.submit(customer_id="alice", project_id="pb", job_id="b")
        with pytest.raises(ValueError):
            workers.submit(customer_id="alice", project_id="pa", job_id="a")
        assert {r.customer_id for r in processing.requests} == {"alice", "bob"}
    finally:
        processing.release.set()
        workers.shutdown()
    assert first.result() == "pa"
    assert second.result() == "pb"
