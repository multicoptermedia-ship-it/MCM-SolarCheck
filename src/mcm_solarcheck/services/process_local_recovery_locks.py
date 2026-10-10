"""Best-effort process-local serialization of explicit recovery attempts.

Not a distributed lock and not a filesystem immutability guarantee.
"""
from __future__ import annotations

import threading


class ProcessLocalRecoveryLocks:
    def __init__(self):
        self._guard = threading.Lock()
        self._locks = {}

    def acquire(self, transfer_id, customer_id, project_id):
        key = (transfer_id, customer_id, project_id)
        if not all(isinstance(value, str) and value for value in key):
            raise ValueError("invalid recovery identity")
        with self._guard:
            lock = self._locks.setdefault(key, threading.Lock())
        return lock.acquire(blocking=False), lock

    @staticmethod
    def release(lock):
        lock.release()
