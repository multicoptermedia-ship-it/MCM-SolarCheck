"""A failed queue scan must be observable and must not kill the scheduler."""
from threading import Event

from mcm_solarcheck.services.automatic_queue_scheduler import AutomaticQueueScheduler


class FlakyPump:
    def __init__(self):
        self.calls = 0
        self.recovered = Event()

    def tick(self):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary database failure")
        self.recovered.set()
        return {}


def test_transient_scan_error_retries_and_remains_visible():
    pump = FlakyPump()
    scheduler = AutomaticQueueScheduler(pump, poll_seconds=0.02)
    try:
        scheduler.start()
        assert pump.recovered.wait(3)
        assert isinstance(scheduler.last_error, RuntimeError)
    finally:
        scheduler.stop(timeout=3)
