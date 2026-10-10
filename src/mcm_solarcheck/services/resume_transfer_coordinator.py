"""Opt-in resume coordinator with externally supplied exclusive transfer lock.

The transport must reject an append unless the remote length equals the verified offset.
"""
from __future__ import annotations

from contextlib import nullcontext
from hashlib import sha256

from mcm_solarcheck.services.resume_preflight import ResumePreflight
from mcm_solarcheck.services.staged_transfer_verifier import StagedTransferVerifier


class ResumeTransferCoordinator:
    def __init__(self, manifests, remote, *, locks, chunk_size: int = 1024 * 1024):
        if locks is None:
            raise ValueError("exclusive transfer locks required")
        if type(chunk_size) is not int or chunk_size <= 0:
            raise ValueError("invalid chunk size")
        self.manifests = manifests
        self.remote = remote
        self.locks = locks
        self.chunk_size = chunk_size
        self.preflight = ResumePreflight(manifests, remote, chunk_size=chunk_size)
        self.verifier = StagedTransferVerifier(manifests, remote, chunk_size=chunk_size)

    def resume(self, transfer_id, customer_id, project_id, source):
        with self.locks.hold(customer_id, project_id, transfer_id):
            row = self.manifests.get(transfer_id, customer_id, project_id)
            if row is None:
                raise PermissionError("transfer not found for owner")
            if row["state"] != "pending":
                return "not_pending"
            inspection = self.preflight.check(transfer_id, customer_id, project_id, source)
            if inspection.status not in ("verified_prefix", "complete_prefix"):
                return inspection.status
            if inspection.status == "verified_prefix":
                # The injected transport must enforce offset matching atomically.
                append = getattr(self.remote, "append_chunks_if_size", None)
                if not callable(append):
                    return "append_unsupported"
                position = source.tell()
                try:
                    source.seek(inspection.verified_offset)

                    def remaining():
                        while True:
                            block = source.read(self.chunk_size)
                            if not block:
                                break
                            if not isinstance(block, bytes) or len(block) > self.chunk_size:
                                raise ValueError("invalid source chunk")
                            yield block

                    append(row["staging_key"], inspection.verified_offset, remaining())
                finally:
                    source.seek(position)
            # Read back the complete staged file before changing metadata.
            outcome = self.verifier.inspect(transfer_id, customer_id, project_id)
            if outcome != "verified_bytes":
                return outcome
            if not self.manifests.transition(
                transfer_id, customer_id, project_id, "pending", "verified"
            ):
                return "state_conflict"
            return "verified"
