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

    def inspect(self, project_directory):
        """Classify pending attempts without modifying files.

        The directory resolver must enforce customer/project isolation.
        Presence alone does not prove that the bytes match an attempt.
        """
        from pathlib import Path

        results = []
        for attempt in self.interrupted():
            try:
                directory = Path(project_directory(attempt.customer_id, attempt.project_id))
                if (
                    not attempt.filename
                    or attempt.filename in {".", ".."}
                    or "/" in attempt.filename
                    or "\\\\" in attempt.filename
                    or "\\x00" in attempt.filename
                ):
                    raise ValueError("invalid filename")
                path = directory / attempt.filename
                if path.is_symlink():
                    status = "unsafe"
                elif path.is_file():
                    status = "file_present_unverified"
                else:
                    status = "file_absent"
            except (OSError, ValueError):
                status = "unsafe"
            results.append((attempt, status))
        return results
