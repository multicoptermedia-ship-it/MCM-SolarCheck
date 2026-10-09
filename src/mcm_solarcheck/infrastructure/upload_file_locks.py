"""Cooperative cross-process upload locks for a trusted local filesystem."""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path


class UploadFileLocks:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def hold(self, customer_id: str, project_id: str, filename: str):
        import fcntl
        from hashlib import sha256

        parts = (customer_id, project_id, filename)
        if any(not isinstance(p, str) or not p or p in (".", "..")
               or "/" in p or chr(92) in p or chr(0) in p for p in parts):
            raise ValueError("invalid lock identity")
        key = sha256("\x00".join(parts).encode("utf-8")).hexdigest()
        path = self.root / (key + ".lock")
        fd = os.open(path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
