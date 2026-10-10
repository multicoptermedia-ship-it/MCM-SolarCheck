"""Descriptor-relative exclusive local publication of a verified source file."""
from __future__ import annotations

import hashlib
import os
import stat


class DescriptorRelativePublisher:
    def __init__(self, *, chunk_size=1024 * 1024):
        if type(chunk_size) is not int or chunk_size <= 0:
            raise ValueError("invalid chunk size")
        self.chunk_size = chunk_size

    def publish(self, source, destination_dir_fd, filename, *, expected_size, expected_sha256):
        if os.name != "posix" or not hasattr(os, "O_NOFOLLOW"):
            raise NotImplementedError("POSIX required")
        if (not isinstance(filename, str) or not filename.endswith(".bin")
                or filename in (".", "..") or "/" in filename or "\\ " in filename
                or filename.startswith(".")):
            raise ValueError("unsafe filename")
        if type(expected_size) is not int or expected_size <= 0:
            raise ValueError("invalid size")
        if (not isinstance(expected_sha256, str) or len(expected_sha256) != 64
                or any(x not in "0123456789abcdef" for x in expected_sha256)):
            raise ValueError("invalid hash")
        info = os.fstat(destination_dir_fd)
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError("invalid destination directory")
        fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise ValueError("unsafe source")
            digest = hashlib.sha256()
            size = 0
            with os.fdopen(os.dup(fd), "rb") as stream:
                while block := stream.read(self.chunk_size):
                    size += len(block)
                    if size > expected_size:
                        raise ValueError("source oversized")
                    digest.update(block)
            if size != expected_size or digest.hexdigest() != expected_sha256:
                raise ValueError("source integrity mismatch")
            after = os.fstat(fd)
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                    before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size,
                                         after.st_mtime_ns, after.st_ctime_ns):
                raise ValueError("source changed during verification")
            os.link(source, filename, dst_dir_fd=destination_dir_fd, follow_symlinks=False)
            os.fsync(destination_dir_fd)
            return filename
        finally:
            os.close(fd)
