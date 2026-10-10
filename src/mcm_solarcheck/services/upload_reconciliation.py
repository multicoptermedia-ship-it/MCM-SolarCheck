"""Conservative opt-in reconciliation of interrupted uploads.

Only journal state is changed. Customer files are never changed.
"""
from __future__ import annotations

from dataclasses import dataclass
from contextlib import nullcontext

from mcm_solarcheck.services.upload_attempt_recovery import UploadAttemptRecovery


@dataclass(frozen=True)
class ReconciliationResult:
    attempt_id: str
    outcome: str


class UploadReconciliation:
    def __init__(self, store, *, file_locks=None):
        self._store = store
        self._file_locks = file_locks
        self._recovery = UploadAttemptRecovery(store)

    def run_once(self, project_directory) -> list[ReconciliationResult]:
        results = []
        for attempt in self._recovery.interrupted():
            lock = (self._file_locks.hold(attempt.customer_id, attempt.project_id, attempt.filename)
                    if self._file_locks is not None else nullcontext())
            with lock:
                # Re-check while holding the same cooperative lock as the upload writer.
                matches = [(a, state) for a, state in
                           self._recovery.inspect_integrity(project_directory)
                           if a.attempt_id == attempt.attempt_id]
                if not matches:
                    continue
                status = matches[0][1]
                if status != "verified":
                    results.append(ReconciliationResult(attempt.attempt_id, "review_" + status))
                    continue
                finalized = self._store.finish_verified_if_unique(attempt.attempt_id)
                results.append(ReconciliationResult(
                    attempt.attempt_id, "completed" if finalized else "review_conflict"
                ))
        return results
