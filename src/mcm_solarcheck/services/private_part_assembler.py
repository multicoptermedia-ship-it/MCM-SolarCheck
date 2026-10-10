"""Opt-in streamed immutable-part assembly into a private temporary file.

Does not publish or replace a customer-visible file.
"""
from __future__ import annotations

import os
import tempfile
from hashlib import sha256
from pathlib import Path

from mcm_solarcheck.services.immutable_upload_parts import immutable_part_key


class PrivatePartAssembler:
    def __init__(self, manifest, remote, *, chunk_size: int = 1024 * 1024):
        if type(chunk_size) is not int or chunk_size <= 0:
            raise ValueError("invalid chunk size")
        self.manifest = manifest
        self.remote = remote
        self.chunk_size = chunk_size

    def assemble(self, transfer_id: str, customer_id: str, project_id: str,
                 *, expected_parts: int, expected_size: int, expected_sha256: str,
                 directory: str | Path) -> Path:
        if type(expected_parts) is not int or expected_parts <= 0:
            raise ValueError("invalid part count")
        if type(expected_size) is not int or expected_size <= 0:
            raise ValueError("invalid size")
        if (not isinstance(expected_sha256, str) or len(expected_sha256) != 64
                or any(c not in "0123456789abcdef" for c in expected_sha256)):
            raise ValueError("invalid SHA-256")
        rows = self.manifest.list_parts(transfer_id, customer_id, project_id)
        if len(rows) != expected_parts or [r["part_number"] for r in rows] != list(range(expected_parts)):
            raise ValueError("incomplete part manifest")
        if sum(row["size"] for row in rows) != expected_size:
            raise ValueError("part sizes differ from expected file size")
        destination = Path(directory)
        if not destination.is_dir() or destination.is_symlink():
            raise ValueError("private assembly directory must exist and not be a symlink")
        name = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb", dir=destination, prefix=".assembly-", delete=False) as output:
                name = Path(output.name)
                total = 0
                overall = sha256()
                for row in rows:
                    key = immutable_part_key(transfer_id, row["part_number"], row["sha256"])
                    if key != row["storage_key"]:
                        raise ValueError("invalid part key")
                    part_digest = sha256()
                    part_size = 0
                    for block in self.remote.read_part_chunks(key, self.chunk_size):
                        if not isinstance(block, bytes) or not block or len(block) > self.chunk_size:
                            raise ValueError("unsafe remote chunk")
                        part_size += len(block)
                        if part_size > row["size"]:
                            raise ValueError("oversized part")
                        part_digest.update(block)
                        overall.update(block)
                        output.write(block)
                    if part_size != row["size"] or part_digest.hexdigest() != row["sha256"]:
                        raise ValueError("part integrity mismatch")
                    total += part_size
                if total != expected_size or overall.hexdigest() != expected_sha256:
                    raise ValueError("complete file integrity mismatch")
                output.flush()
                os.fsync(output.fileno())
            return name
        except BaseException:
            if name is not None:
                name.unlink(missing_ok=True)
            raise
