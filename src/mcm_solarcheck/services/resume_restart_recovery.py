"""Read-only restart reconciliation of durable staged transfers.

Never marks a transfer published or appends bytes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO

from mcm_solarcheck.services.resume_preflight import ResumePreflight


@dataclass(frozen=True)
class RestartInspection:
    transfer_id: str
    status: str
    verified_offset: int = 0


class ResumeRestartRecovery:
    def __init__(self, manifests, remote, *, locks, chunk_size: int = 1024 * 1024):
        if locks is None:
            raise ValueError("exclusive locks required")
        self.manifests = manifests
        self.locks = locks
        self.preflight = ResumePreflight(manifests, remote, chunk_size=chunk_size)

    def inspect(self, transfer_id: str, customer_id: str, project_id: str,
                source: BinaryIO) -> RestartInspection:
        with self.locks.hold(customer_id, project_id, transfer_id):
            result = self.preflight.check(transfer_id, customer_id, project_id, source)
            return RestartInspection(transfer_id, result.status, result.verified_offset)
