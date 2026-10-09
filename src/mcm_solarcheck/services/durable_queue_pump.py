"""Explicit durable-queue scan and dispatch cycle.

Scheduling is invoked by a deployment scheduler; no background thread is started.
"""
from __future__ import annotations

from mcm_solarcheck.services.queued_job_dispatcher import PendingProjectJob


class DurableQueuePump:
    def __init__(self, store, dispatcher, *, batch_size: int = 100):
        if type(batch_size) is not int or batch_size <= 0:
            raise ValueError("batch_size must be a positive integer")
        self._store = store
        self._dispatcher = dispatcher
        self._batch_size = batch_size

    def tick(self):
        """Read FIFO persisted jobs and attempt atomic admission to workers."""
        queued = self._store.queued_jobs(limit=self._batch_size)
        return self._dispatcher.dispatch([
            PendingProjectJob(job.user_id, job.project_id, job.job_id)
            for job in queued
        ])
