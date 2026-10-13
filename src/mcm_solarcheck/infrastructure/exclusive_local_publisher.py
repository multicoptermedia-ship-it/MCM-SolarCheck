"""Exclusive local publication of an already assembled private file.

This is a local-filesystem prototype, not an SFTP publishing implementation.
"""
from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path


class ExclusiveLocalPublisher:
    def __init__(self, *, chunk_size: int = 1024 * 1024):
        if type(chunk_size) is not int or chunk_size <= 0:
            raise ValueError("invalid chunk size")
        self.chunk_size = chunk_size

    def publish(self, source, destination, *, expected_size: int, expected_sha256: str) -> Path:
        source = Path(source)
        destination = Path(destination)
        if type(expected_size) is not int or expected_size <= 0:
            raise ValueError("invalid expected size")
        if (not isinstance(expected_sha256, str) or len(expected_sha256) != 64
                or any(c not in "0123456789abcdef" for c in expected_sha256)):
            raise ValueError("invalid SHA-256")
        if not source.name.startswith(".assembly-"):
            raise ValueError("source must be a private assembly file")
        if not source.parent.is_dir() or source.parent.is_symlink():
            raise ValueError("unsafe source directory")
        if not destination.parent.is_dir() or destination.parent.is_symlink():
            raise ValueError("unsafe destination directory")
        if destination.name in ("", ".", "..") or destination.name.startswith("."):
            raise ValueError("invalid destination name")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(source, flags)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise ValueError("source is not a private regular file")
            digest = hashlib.sha256()
            total = 0
            with os.fdopen(os.dup(fd), "rb") as stream:
                while True:
                    block = stream.read(self.chunk_size)
                    if not block:
                        break
                    total += len(block)
                    if total > expected_size:
                        raise ValueError("source too large")
                    digest.update(block)
            if total != expected_size or digest.hexdigest() != expected_sha256:
                raise ValueError("source integrity mismatch")
            after = os.fstat(fd)
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                    before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size,
                                         after.st_mtime_ns, after.st_ctime_ns):
                raise ValueError("source changed during verification")
            if os.stat(source, follow_symlinks=False).st_ino != before.st_ino:
                raise ValueError("source path changed")
            # Hard-link creation fails if the final name already exists.
            # Same-filesystem constraint is intentional; no copy-to-final fallback.
            os.link(source, destination, follow_symlinks=False)
            try:
                dirfd = os.open(destination.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
                try:
                    os.fsync(dirfd)
                finally:
                    os.close(dirfd)
            except OSError:
                # Publication may already have happened. Never unlink the final path here.
                raise
            return destination
        finally:
            os.close(fd)
