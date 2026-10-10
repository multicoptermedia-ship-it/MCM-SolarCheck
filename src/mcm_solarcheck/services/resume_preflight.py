"""Fail-closed preflight for a future resumable staged transfer.

A successful preflight is advisory only, never permission to append remotely.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO

from mcm_solarcheck.services.resume_source_integrity import verify_resume_source
from mcm_solarcheck.services.staged_resume_inspector import StagedResumeInspector


@dataclass(frozen=True)
class ResumePreflightResult:
    status: str
    verified_offset: int = 0


class ResumePreflight:
    def __init__(self, manifests, remote, *, chunk_size: int = 1024 * 1024):
        self.manifests = manifests
        self.inspector = StagedResumeInspector(manifests, remote, chunk_size=chunk_size)
        self.chunk_size = chunk_size

    def check(self, transfer_id: str, customer_id: str, project_id: str,
              source: BinaryIO) -> ResumePreflightResult:
        row = self.manifests.get(transfer_id, customer_id, project_id)
        if row is None:
            raise PermissionError("transfer not found for owner")
        if row["state"] != "pending":
            return ResumePreflightResult("not_pending")
        original_position = source.tell()
        try:
            if not verify_resume_source(
                source, expected_size=row["expected_size"],
                expected_sha256=row["expected_sha256"], chunk_size=self.chunk_size
            ):
                return ResumePreflightResult("source_mismatch")
            source.seek(0)
            result = self.inspector.inspect(transfer_id, customer_id, project_id, source)
            return ResumePreflightResult(result.status, result.verified_offset)
        finally:
            source.seek(original_position)
