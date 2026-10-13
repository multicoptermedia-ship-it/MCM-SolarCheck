"""Failed processing remains observable to the submitting worker caller."""
from types import SimpleNamespace

import pytest

from mcm_solarcheck.services.compute_jobs import ComputeJobStatus
from mcm_solarcheck.services.parallel_processing_workers import ParallelProjectWorkers


class Jobs:
    def get(self, job_id, *, user_id, project_id):
        return SimpleNamespace(status=ComputeJobStatus.RUNNING)


class Processing:
    def process(self, request):
        raise RuntimeError("import failed")


def test_processing_failure_surfaces_through_future():
    workers = ParallelProjectWorkers(Jobs(), Processing())
    try:
        future = workers.submit(customer_id="alice", project_id="p", job_id="j")
        with pytest.raises(RuntimeError, match="import failed"):
            future.result(timeout=3)
    finally:
        workers.shutdown()


@pytest.mark.parametrize("value", [0, -1, True, 1.5])
def test_invalid_worker_capacity_rejected(value):
    with pytest.raises(ValueError):
        ParallelProjectWorkers(Jobs(), Processing(), max_workers=value)
