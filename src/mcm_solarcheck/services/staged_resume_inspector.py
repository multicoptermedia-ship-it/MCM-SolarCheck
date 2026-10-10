"""Read-only prefix verification for a resumable staged upload.

No offset is authorized for writing by this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import BinaryIO


@dataclass(frozen=True)
class ResumeInspection:
    status: str
    verified_offset: int = 0


class StagedResumeInspector:
    def __init__(self, manifests, remote, *, chunk_size: int = 1024 * 1024):
        if type(chunk_size) is not int or chunk_size <= 0:
            raise ValueError("invalid chunk size")
        self.manifests = manifests
        self.remote = remote
        self.chunk_size = chunk_size

    def inspect(self, transfer_id: str, customer_id: str, project_id: str,
                source: BinaryIO) -> ResumeInspection:
        row = self.manifests.get(transfer_id, customer_id, project_id)
        if row is None:
            raise PermissionError("transfer not found for owner")
        if row["state"] != "pending":
            return ResumeInspection("not_pending")
        offset = 0
        try:
            for block in self.remote.read_staging_chunks(row["staging_key"], self.chunk_size):
                if not isinstance(block, bytes) or not block or len(block) > self.chunk_size:
                    return ResumeInspection("unsafe_chunk")
                offset += len(block)
                if offset > row["expected_size"]:
                    return ResumeInspection("size_mismatch")
                reference = source.read(len(block))
                if not isinstance(reference, bytes) or reference != block:
                    return ResumeInspection("prefix_mismatch")
        except OSError:
            return ResumeInspection("unavailable")
        if offset == row["expected_size"]:
            return ResumeInspection("complete_prefix", offset)
        return ResumeInspection("verified_prefix", offset)
