"""A full worker pool rejects extra tasks without blocking the caller."""
from threading import Event
from types import SimpleNamespace

import pytest

from mcm_solarcheck.services.compute_jobs import ComputeJobStatus
from mcm_solarcheck.services.parallel_processing_workers import ParallelProjectWorkers


class Jobs:
    def get(self, job_id, *, user_id, project_id):
        return SimpleNamespace(status=ComputeJobStatus.RUNNING)


class Processing:
    def __init__(self):
        self.started = Event()
        self.release = Event()

    def process(self, request):
        self.started.set()
        assert self.release.wait(5)
        return request.job_id


def test_pool_rejects_third_while_two_are_busy():
    processing = Processing()
    workers = ParallelProjectWorkers(Jobs(), processing, max_workers=2)
    try:
        first = workers.submit(customer_id="a", project_id="a", job_id="a")
        assert processing.started.wait(3)
        second = workers.submit(customer_id="b", project_id="b", job_id="b")
        with pytest.raises(RuntimeError, match="capacity exhausted"):
            workers.submit(customer_id="c", project_id="c", job_id="c")
    finally:
        processing.release.set()
        workers.shutdown()
    assert first.result() == "a"
    assert second.result() == "b"
