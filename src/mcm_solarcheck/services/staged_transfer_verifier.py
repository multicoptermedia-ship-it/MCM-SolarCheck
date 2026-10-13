"""Read-only verification of remote staging before a resumed transfer is trusted."""
from __future__ import annotations

from hashlib import sha256
from typing import Iterable


class StagedTransferVerifier:
    def __init__(self, manifest, remote, *, chunk_size: int = 1024 * 1024):
        if type(chunk_size) is not int or chunk_size <= 0:
            raise ValueError("invalid chunk size")
        self.manifest = manifest
        self.remote = remote
        self.chunk_size = chunk_size

    def inspect(self, transfer_id: str, customer_id: str, project_id: str) -> str:
        row = self.manifest.get(transfer_id, customer_id, project_id)
        if row is None:
            raise PermissionError("transfer not found for owner")
        if row["state"] != "pending":
            return "not_pending"
        digest = sha256()
        size = 0
        try:
            chunks: Iterable[bytes] = self.remote.read_staging_chunks(
                row["staging_key"], self.chunk_size
            )
            for block in chunks:
                if not isinstance(block, bytes) or len(block) > self.chunk_size:
                    return "unsafe_chunk"
                size += len(block)
                if size > row["expected_size"]:
                    return "size_mismatch"
                digest.update(block)
        except (OSError, FileNotFoundError):
            return "unavailable"
        if size != row["expected_size"]:
            return "size_mismatch"
        if digest.hexdigest() != row["expected_sha256"]:
            return "hash_mismatch"
        return "verified_bytes"
