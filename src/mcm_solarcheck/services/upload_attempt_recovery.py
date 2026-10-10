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
                    or chr(92) in attempt.filename
                    or chr(0) in attempt.filename
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

    def inspect_integrity(self, project_directory):
        """Verify pending uploads against journaled bytes, without modifying data."""
        from hashlib import sha256
        from pathlib import Path
        import os
        import stat

        results = []
        for row in self._store.pending_with_integrity():
            attempt = InterruptedUpload(*row[:4])
            expected_size, expected_hash = row[4:]
            try:
                if (not attempt.filename or attempt.filename in {".", ".."}
                        or "/" in attempt.filename or chr(92) in attempt.filename
                        or chr(0) in attempt.filename):
                    raise ValueError("unsafe filename")
                directory = Path(project_directory(attempt.customer_id, attempt.project_id))
                path = directory / attempt.filename
                if path.is_symlink():
                    status = "unsafe"
                elif not path.is_file():
                    status = "file_absent"
                elif expected_size is None or expected_hash is None:
                    status = "file_present_unverified"
                else:
                    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                    if not hasattr(os, "O_NOFOLLOW"):
                        status = "unsafe"
                    else:
                        fd = os.open(path, flags)
                        try:
                            before = os.fstat(fd)
                            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                                status = "unsafe"
                            elif before.st_size != expected_size:
                                status = "size_mismatch"
                            else:
                                digest = sha256()
                                with os.fdopen(os.dup(fd), "rb") as source:
                                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                                        digest.update(chunk)
                                after = os.fstat(fd)
                                stable = (
                                    before.st_dev == after.st_dev
                                    and before.st_ino == after.st_ino
                                    and before.st_size == after.st_size
                                    and before.st_mtime_ns == after.st_mtime_ns
                                    and before.st_ctime_ns == after.st_ctime_ns
                                )
                                if not stable:
                                    status = "unsafe"
                                else:
                                    status = "verified" if digest.hexdigest() == expected_hash else "hash_mismatch"
                        finally:
                            os.close(fd)
            except (OSError, ValueError):
                status = "unsafe"
            results.append((attempt, status))
        return results
