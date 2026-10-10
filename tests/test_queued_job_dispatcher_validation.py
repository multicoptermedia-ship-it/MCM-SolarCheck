"""Reject invalid dispatch identities and capacity."""
import pytest

from mcm_solarcheck.services.queued_job_dispatcher import PendingProjectJob, QueuedJobDispatcher


@pytest.mark.parametrize("customer,project,job", [("", "p", "j"), ("u", "", "j"), ("u", "p", " "), (None, "p", "j")])
def test_pending_identity_validation(customer, project, job):
    with pytest.raises(ValueError):
        PendingProjectJob(customer, project, job)


@pytest.mark.parametrize("capacity", [0, -1, True, 1.5])
def test_invalid_dispatch_capacity(capacity):
    with pytest.raises(ValueError):
        QueuedJobDispatcher(None, None, max_parallel_jobs=capacity)
