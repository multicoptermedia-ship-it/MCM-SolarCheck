"""Cross-process cooperative lock for local administrator credential mutations.

A stable .lock file must never be unlinked: deleting an existing lock name
while another process holds an inode lock defeats the coordination protocol.
Linux/macOS use flock; Windows uses msvcrt byte-range locking.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import stat
import sys
from typing import Iterator


@contextmanager
def credential_mutation_lock(credential_path: Path) -> Iterator[None]:
    if (
        not credential_path.is_absolute()
        or not credential_path.parent.is_dir()
        or any(part.is_symlink() for part in (credential_path, *credential_path.parents))
    ):
        raise PermissionError("unsafe administrator credential path")
    path = credential_path.with_name(credential_path.name + ".lock")
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or (
            os.name == "posix" and info.st_mode & 0o077
        ):
            raise PermissionError("unsafe administrator credential lock")
        if sys.platform == "win32":
            import msvcrt
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
