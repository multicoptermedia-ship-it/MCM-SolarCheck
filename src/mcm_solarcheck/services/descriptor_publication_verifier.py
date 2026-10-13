"""Read-only integrity verification using a pinned POSIX project directory."""
from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path

from mcm_solarcheck.infrastructure.private_directory_descriptors import open_private_directory_chain
from mcm_solarcheck.services.canonical_local_destination import canonical_local_destination


class DescriptorPublicationVerifier:
    def __init__(self, root, *, chunk_size=1024 * 1024):
        self.root = Path(root)
        if not self.root.is_absolute() or self.root.is_symlink() or not self.root.is_dir():
            raise ValueError("trusted existing root required")
        if type(chunk_size) is not int or chunk_size <= 0:
            raise ValueError("invalid chunk size")
        self.chunk_size = chunk_size

    def inspect(self, transfer_id, customer_id, project_id, *, expected_size, expected_sha256):
        final = canonical_local_destination(self.root, customer_id, project_id, transfer_id)
        if type(expected_size) is not int or expected_size <= 0:
            raise ValueError("invalid size")
        if not isinstance(expected_sha256, str) or len(expected_sha256) != 64 or any(
            c not in "0123456789abcdef" for c in expected_sha256
        ):
            raise ValueError("invalid digest")
        try:
            directory_fd = open_private_directory_chain(self.root, customer_id, project_id)
        except FileNotFoundError:
            return "missing_final"
        except (OSError, NotImplementedError):
            return "unavailable"
        try:
            try:
                fd = os.open(final.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
            except FileNotFoundError:
                return "missing_final"
            except OSError:
                return "unavailable"
            try:
                before = os.fstat(fd)
                if not stat.S_ISREG(before.st_mode) or before.st_size != expected_size:
                    return "invalid_final"
                digest = hashlib.sha256()
                total = 0
                with os.fdopen(os.dup(fd), "rb") as stream:
                    while block := stream.read(self.chunk_size):
                        total += len(block)
                        if total > expected_size:
                            return "invalid_final"
                        digest.update(block)
                after = os.fstat(fd)
                if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                        before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size,
                                               after.st_mtime_ns, after.st_ctime_ns):
                    return "changed_during_read"
                if total != expected_size or digest.hexdigest() != expected_sha256:
                    return "invalid_final"
                return "verified_final"
            except OSError:
                return "unavailable"
            finally:
                os.close(fd)
        finally:
            os.close(directory_fd)
