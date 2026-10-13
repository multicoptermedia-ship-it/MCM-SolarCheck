"""Read-only reconciliation of journal entries with local published file bytes."""
from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path


class LocalPublicationReconciler:
    def __init__(self, journal, *, chunk_size=1024 * 1024):
        if type(chunk_size) is not int or chunk_size <= 0:
            raise ValueError("invalid chunk size")
        self.journal = journal
        self.chunk_size = chunk_size

    def inspect(self, transfer_id, customer_id, project_id):
        record = self.journal.get(transfer_id, customer_id, project_id)
        if record is None:
            return "not_found"
        if record["state"] == "published":
            return "already_recorded"
        path = Path(record["destination"])
        try:
            fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        except FileNotFoundError:
            return "missing_final"
        except OSError:
            return "unavailable"
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size != record["expected_size"]:
                return "invalid_final"
            digest = hashlib.sha256()
            total = 0
            with os.fdopen(os.dup(fd), "rb") as stream:
                while block := stream.read(self.chunk_size):
                    total += len(block)
                    if total > record["expected_size"]:
                        return "invalid_final"
                    digest.update(block)
            after = os.fstat(fd)
            if (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns
            ):
                return "changed_during_read"
            if total != record["expected_size"] or digest.hexdigest() != record["expected_sha256"]:
                return "invalid_final"
            return "verified_final"
        except OSError:
            return "unavailable"
        finally:
            os.close(fd)
