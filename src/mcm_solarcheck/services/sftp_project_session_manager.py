"""Bounded, project-scoped SFTP session leases for an injected verified connector.

This in-process limit is not a distributed worker queue or a storage permission boundary.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from threading import BoundedSemaphore
import re

_TOKEN = re.compile(r"[A-Za-z0-9_-]{1,100}\Z")


@dataclass(frozen=True)
class SFTPProjectContext:
    customer_id: str
    project_id: str

    def __post_init__(self):
        for value in (self.customer_id, self.project_id):
            if not isinstance(value, str) or _TOKEN.fullmatch(value) is None:
                raise ValueError("invalid customer or project identifier")


class SFTPProjectSessionManager:
    """Leases at most max_sessions sessions within this Python process."""

    def __init__(self, connector, config, *, max_sessions=2):
        if isinstance(max_sessions, bool) or not isinstance(max_sessions, int) or max_sessions < 1:
            raise ValueError("max_sessions must be a positive integer")
        self._connector = connector
        self._config = config
        self._slots = BoundedSemaphore(max_sessions)

    @contextmanager
    def lease(self, context: SFTPProjectContext):
        if not isinstance(context, SFTPProjectContext):
            raise TypeError("SFTPProjectContext required")
        self._slots.acquire()
        try:
            with self._connector.open_verified_read_only(self._config) as session:
                yield SFTPProjectSession(context=context, session=session)
        finally:
            self._slots.release()


@dataclass(frozen=True)
class SFTPProjectSession:
    context: SFTPProjectContext
    session: object

    def directory_exists(self, context: SFTPProjectContext, path: str) -> bool:
        if context != self.context:
            raise PermissionError("SFTP project context mismatch")
        if not isinstance(path, str) or not path.startswith("/"):
            raise ValueError("absolute SFTP directory path required")
        return self.session.directory_exists(path)
