"""Read-only reconciliation view for interrupted upload attempts."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InterruptedUpload:
    attempt_id: str
    customer_id: str
    project_id: str
    filename: str


class UploadAttemptRecovery:
    def __init__(self, store):
        self._store = store

    def interrupted(self) -> list[InterruptedUpload]:
        return [InterruptedUpload(*row) for row in self._store.pending()]
