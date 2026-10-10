"""External queue notifications trigger a scan without waiting for the poll interval."""
from threading import Event

from mcm_solarcheck.services.automatic_queue_scheduler import AutomaticQueueScheduler


class Pump:
    def __init__(self):
        self.calls = 0
        self.initial = Event()
        self.notified = Event()

    def tick(self):
        self.calls += 1
        if self.calls == 1:
            self.initial.set()
        else:
            self.notified.set()
        return {}


def test_new_job_notification_wakes_scheduler():
    pump = Pump()
    scheduler = AutomaticQueueScheduler(pump, poll_seconds=30)
    try:
        scheduler.start()
        assert pump.initial.wait(3)
        scheduler.notify()
        assert pump.notified.wait(3)
    finally:
        scheduler.stop(timeout=3)
