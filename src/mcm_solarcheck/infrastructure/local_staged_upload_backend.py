"""Local test adapter for staged delivery; not an SFTP adapter."""
from __future__ import annotations

import os
from pathlib import Path


class LocalStagedUploadBackend:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        if not key or key.startswith("/") or chr(92) in key or chr(0) in key:
            raise ValueError("invalid storage key")
        parts = key.split("/")
        if any(p in ("", ".", "..") for p in parts):
            raise ValueError("invalid storage key")
        path = self.root.joinpath(*parts)
        if path.resolve() != path.absolute() or not path.resolve().is_relative_to(self.root):
            raise ValueError("unsafe storage path")
        return path

    def put_staging(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())

    def read_staging(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def publish(self, staging_key: str, final_key: str) -> None:
        source = self._path(staging_key)
        target = self._path(final_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            raise FileExistsError("published upload already exists")
        os.link(source, target)
        fd = os.open(target.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def remove_staging(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)
