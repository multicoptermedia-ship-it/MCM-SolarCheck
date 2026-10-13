"""Bounded opt-in inspection of durable queue snapshots; no job state changes."""
from __future__ import annotations

from mcm_solarcheck.services.queued_job_dispatcher import PendingProjectJob


class QueuedSFTPPreflightBatch:
    def __init__(self, store, preflight, *, batch_size=100):
        if type(batch_size) is not int or batch_size <= 0:
            raise ValueError("batch_size must be a positive integer")
        self._store = store
        self._preflight = preflight
        self._batch_size = batch_size

    def tick(self):
        results = []
        seen = set()
        for job in self._store.queued_jobs(limit=self._batch_size):
            if job.job_id in seen:
                continue
            seen.add(job.job_id)
            results.append(self._preflight.inspect(
                PendingProjectJob(job.user_id, job.project_id, job.job_id)
            ))
        return results
