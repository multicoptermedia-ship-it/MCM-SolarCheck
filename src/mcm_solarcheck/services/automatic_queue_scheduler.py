"""Opt-in background scheduler for a durable queue pump.

Only the hosting process owns the thread; deployment must manage lifecycle and
multi-process exclusivity. Worker futures own processing outcomes.
"""
from __future__ import annotations

from threading import Event, Lock, Thread


class AutomaticQueueScheduler:
    def __init__(self, pump, *, poll_seconds: float = 1.0):
        if isinstance(poll_seconds, bool) or not isinstance(poll_seconds, (int, float)) or not 0 < poll_seconds <= 3600:
            raise ValueError("poll_seconds must be between 0 and 3600")
        self._pump = pump
        self._poll_seconds = float(poll_seconds)
        self._wake = Event()
        self._stop = Event()
        self._lock = Lock()
        self._thread: Thread | None = None
        self._last_error: Exception | None = None

    @property
    def last_error(self) -> Exception | None:
        with self._lock:
            return self._last_error

    def start(self) -> None:
        """Start one daemon scheduler, with an immediate initial queue scan."""
        with self._lock:
            if self._thread is not None:
                raise RuntimeError("queue scheduler already started")
            self._stop.clear()
            self._wake.set()
            self._thread = Thread(target=self._run, name="solarcheck-queue", daemon=True)
            self._thread.start()

    def notify(self) -> None:
        """Wake the queue scan when a new job is enqueued."""
        self._wake.set()

    def stop(self, *, timeout: float | None = None) -> None:
        with self._lock:
            thread = self._thread
        if thread is None:
            return
        self._stop.set()
        self._wake.set()
        thread.join(timeout=timeout)
        if thread.is_alive():
            raise TimeoutError("queue scheduler did not stop")
        with self._lock:
            if self._thread is thread:
                self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            self._wake.wait(timeout=self._poll_seconds)
            self._wake.clear()
            if self._stop.is_set():
                break
            try:
                futures = self._pump.tick()
                for future in futures.values():
                    future.add_done_callback(lambda _finished: self.notify())
            except Exception as error:
                with self._lock:
                    self._last_error = error
