"""Conservative opt-in reconciliation of interrupted uploads.

Only journal state is changed. Customer files are never changed.
"""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.upload_attempt_recovery import UploadAttemptRecovery


@dataclass(frozen=True)
class ReconciliationResult:
    attempt_id: str
    outcome: str


class UploadReconciliation:
    def __init__(self, store):
        self._store = store
        self._recovery = UploadAttemptRecovery(store)

    def run_once(self, project_directory) -> list[ReconciliationResult]:
        results = []
        for attempt, status in self._recovery.inspect_integrity(project_directory):
            if status != "verified":
                results.append(ReconciliationResult(attempt.attempt_id, "review_" + status))
                continue
            finalized = self._store.finish_verified_if_unique(attempt.attempt_id)
            results.append(ReconciliationResult(
                attempt.attempt_id, "completed" if finalized else "review_conflict"
            ))
        return results
