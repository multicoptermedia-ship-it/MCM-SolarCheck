"""Isolated opt-in queue scan: one SFTP failure cannot stop later jobs."""
from __future__ import annotations

from mcm_solarcheck.services.queued_job_dispatcher import PendingProjectJob
from mcm_solarcheck.services.sftp_preflight_outcomes import classify_preflight_outcome


class IsolatedQueuedSFTPPreflightBatch:
    def __init__(self, store, preflight, *, batch_size=100):
        if type(batch_size) is not int or batch_size <= 0:
            raise ValueError("batch_size must be a positive integer")
        self._store = store
        self._preflight = preflight
        self._batch_size = batch_size

    def tick(self):
        outcomes = []
        seen = set()
        for raw in self._store.queued_jobs(limit=self._batch_size):
            job = PendingProjectJob(raw.user_id, raw.project_id, raw.job_id)
            if job.job_id in seen:
                continue
            seen.add(job.job_id)
            try:
                inspection = self._preflight.inspect(job)
            except Exception as error:
                outcomes.append(classify_preflight_outcome(job, error=error))
            else:
                outcomes.append(classify_preflight_outcome(job, inspection=inspection))
        return outcomes
