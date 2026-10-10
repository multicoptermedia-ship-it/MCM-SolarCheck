"""Private filesystem storage for validated online project uploads."""

from __future__ import annotations

import os
import tempfile
from contextlib import nullcontext
from pathlib import Path

from mcm_solarcheck.services.project_upload import ValidatedProjectUpload


class FileSystemProjectUploadStore:
    def __init__(self, root: str | Path, *, file_locks=None) -> None:
        self.file_locks = file_locks
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _segment(value: str, field: str) -> str:
        normalized = value.strip()
        if (
            not normalized
            or normalized in {".", ".."}
            or "/" in normalized
            or "\\" in normalized
            or "\x00" in normalized
        ):
            raise ValueError(f"{field} is invalid")
        return normalized

    def project_directory(self, customer_id: str, project_id: str) -> Path:
        customer = self._segment(customer_id, "customer_id")
        project = self._segment(project_id, "project_id")
        directory = self.root / customer / project
        try:
            directory.resolve().relative_to(self.root)
        except ValueError as exc:
            raise ValueError("project upload directory resolves outside configured root") from exc
        return directory

    def store(self, upload: ValidatedProjectUpload) -> None:
        request = upload.request
        lock = (self.file_locks.hold(request.customer_id, request.project_id, request.filename)
                if self.file_locks is not None else nullcontext())
        with lock:
            self._store_locked(upload)

    def _store_locked(self, upload: ValidatedProjectUpload) -> None:
        request = upload.request
        filename = self._segment(request.filename, "filename")
        directory = self.project_directory(request.customer_id, request.project_id)
        directory.mkdir(parents=True, exist_ok=True)
        try:
            directory.resolve().relative_to(self.root)
        except ValueError as exc:
            raise ValueError("project upload directory resolves outside configured root") from exc
        destination = directory / filename
        try:
            destination.resolve().relative_to(self.root)
        except ValueError as exc:
            raise ValueError("project upload file resolves outside configured root") from exc
        try:
            destination.parent.resolve().relative_to(self.root)
        except ValueError as exc:
            raise ValueError("project upload directory resolves outside configured root") from exc
        if destination.is_symlink() and not destination.exists():
            raise ValueError("project upload destination must not be a dangling symlink")
        if destination.exists() and not destination.is_file():
            raise ValueError("project upload destination must be a regular file")
        if destination.exists() and destination.stat().st_nlink > 1:
            raise ValueError("project upload destination must not be hard-linked")
        # Replace the resolved target atomically; internal symlinks retain their
        # existing semantics without truncating a previously valid upload.
        target = destination.resolve()
        temporary = None
        try:
            descriptor, name = tempfile.mkstemp(prefix=".upload-", dir=target.parent)
            temporary = Path(name)
            with os.fdopen(descriptor, "wb") as output:
                output.write(request.content)
                output.flush()
                os.fsync(output.fileno())
            try:
                target.relative_to(self.root)
                destination.resolve().relative_to(self.root)
            except ValueError as exc:
                raise ValueError("project upload file resolves outside configured root") from exc
            if destination.resolve() != target:
                raise ValueError("project upload destination changed during storage")
            os.replace(temporary, target)
            directory_fd = os.open(target.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
