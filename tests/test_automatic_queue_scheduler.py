"""Scheduler automatically scans queue and wakes when a worker completes."""
from concurrent.futures import Future
from threading import Event

import pytest

from mcm_solarcheck.services.automatic_queue_scheduler import AutomaticQueueScheduler


class Pump:
    def __init__(self):
        self.calls = 0
        self.first = Event()
        self.second = Event()
        self.future = Future()

    def tick(self):
        self.calls += 1
        if self.calls == 1:
            self.first.set()
            return {"j1": self.future}
        self.second.set()
        return {}


def test_initial_scan_and_completion_wakeup():
    pump = Pump()
    scheduler = AutomaticQueueScheduler(pump, poll_seconds=30)
    try:
        scheduler.start()
        assert pump.first.wait(3)
        pump.future.set_result("done")
        assert pump.second.wait(3)
    finally:
        scheduler.stop(timeout=3)


def test_reject_double_start_and_allow_restart():
    scheduler = AutomaticQueueScheduler(Pump(), poll_seconds=30)
    try:
        scheduler.start()
        with pytest.raises(RuntimeError, match="already started"):
            scheduler.start()
    finally:
        scheduler.stop(timeout=3)
    scheduler.start()
    scheduler.stop(timeout=3)


@pytest.mark.parametrize("value", [0, -1, True, 3601, "1"])
def test_invalid_poll_interval(value):
    with pytest.raises(ValueError):
        AutomaticQueueScheduler(Pump(), poll_seconds=value)
