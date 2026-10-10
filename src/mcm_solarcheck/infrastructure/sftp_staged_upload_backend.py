"""SFTP staged-upload adapter using an injected, capability-checked transport.

No network connection or credentials are created here.
"""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Protocol


class SFTPPublishUnsupported(RuntimeError):
    """The transport cannot guarantee no-overwrite publication."""


class SFTPTransport(Protocol):
    def write_exclusive(self, path: str, data: bytes) -> None: ...
    def read(self, path: str) -> bytes: ...
    def remove(self, path: str) -> None: ...
    def publish_exclusive(self, source: str, destination: str) -> None: ...


class SFTPStagedUploadBackend:
    def __init__(self, transport: SFTPTransport, *, root: str):
        if not root.startswith("/") or root == "/" or any(
            p in (".", "..") for p in root.split("/") if p
        ) or chr(92) in root or chr(0) in root:
            raise ValueError("absolute private SFTP root required")
        self.transport = transport
        self.root = root.rstrip("/")

    def _remote(self, key: str) -> str:
        if not key or key.startswith("/") or chr(92) in key or chr(0) in key:
            raise ValueError("invalid SFTP key")
        parts = key.split("/")
        if any(part in ("", ".", "..") for part in parts):
            raise ValueError("invalid SFTP key")
        return str(PurePosixPath(self.root, *parts))

    def put_staging(self, key: str, data: bytes) -> None:
        if not key.startswith(".staging/"):
            raise ValueError("staging key required")
        self.transport.write_exclusive(self._remote(key), data)

    def read_staging(self, key: str) -> bytes:
        return self.transport.read(self._remote(key))

    def publish(self, staging_key: str, final_key: str) -> None:
        if not staging_key.startswith(".staging/") or final_key.startswith(".staging/"):
            raise ValueError("invalid publication")
        method = getattr(self.transport, "publish_exclusive", None)
        if not callable(method):
            raise SFTPPublishUnsupported("transport lacks exclusive publication")
        method(self._remote(staging_key), self._remote(final_key))

    def remove_staging(self, key: str) -> None:
        if not key.startswith(".staging/"):
            raise ValueError("staging key required")
        self.transport.remove(self._remote(key))
