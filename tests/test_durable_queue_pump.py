"""Pump hands persisted identities to the existing dispatcher."""
from types import SimpleNamespace

import pytest

from mcm_solarcheck.services.durable_queue_pump import DurableQueuePump
from mcm_solarcheck.services.queued_job_dispatcher import PendingProjectJob


class Store:
    def queued_jobs(self, *, limit):
        assert limit == 2
        return [
            SimpleNamespace(job_id="j1", user_id="alice", project_id="pa"),
            SimpleNamespace(job_id="j2", user_id="bob", project_id="pb"),
        ]


class Dispatcher:
    def __init__(self):
        self.items = []

    def dispatch(self, pending):
        self.items = pending
        return {"j1": object(), "j2": object()}


def test_pump_scans_and_dispatches_customer_scoped_jobs():
    dispatcher = Dispatcher()
    result = DurableQueuePump(Store(), dispatcher, batch_size=2).tick()
    assert set(result) == {"j1", "j2"}
    assert dispatcher.items == [
        PendingProjectJob("alice", "pa", "j1"),
        PendingProjectJob("bob", "pb", "j2"),
    ]


@pytest.mark.parametrize("value", [0, -1, True, 1.5])
def test_invalid_batch_size(value):
    with pytest.raises(ValueError):
        DurableQueuePump(Store(), Dispatcher(), batch_size=value)
