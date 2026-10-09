"""Bounded in-process execution of already admitted, customer-scoped project jobs.

Deployment must supply a durable queue and recovery strategy separately.
"""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock

from mcm_solarcheck.services.compute_jobs import ComputeJobStatus
from mcm_solarcheck.services.project_processing import ProjectProcessingRequest


class ParallelProjectWorkers:
    """Execute at most max_workers imports concurrently, never inventing findings."""

    def __init__(self, jobs, processing, *, max_workers: int = 2):
        if type(max_workers) is not int or max_workers <= 0:
            raise ValueError("max_workers must be a positive integer")
        self._jobs = jobs
        self._processing = processing
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="solarcheck-project")
        self._lock = Lock()
        self._active: dict[str, Future] = {}
        self._max_workers = max_workers

    def submit(self, *, customer_id: str, project_id: str, job_id: str) -> Future:
        """Require authoritative ownership and running admission before scheduling."""
        job = self._jobs.get(job_id, user_id=customer_id, project_id=project_id)
        if job.status is not ComputeJobStatus.RUNNING:
            raise ValueError("only admitted running jobs can be submitted")
        with self._lock:
            if job_id in self._active:
                raise ValueError("job already submitted to this worker pool")
            if len(self._active) >= self._max_workers:
                raise RuntimeError("worker pool capacity exhausted")
            future = self._pool.submit(
                self._processing.process,
                ProjectProcessingRequest(customer_id, project_id, job_id),
            )
            self._active[job_id] = future
            future.add_done_callback(lambda finished, key=job_id: self._discard(key, finished))
            return future

    def _discard(self, job_id: str, future: Future) -> None:
        with self._lock:
            if self._active.get(job_id) is future:
                del self._active[job_id]

    def shutdown(self, *, wait: bool = True) -> None:
        self._pool.shutdown(wait=wait)
