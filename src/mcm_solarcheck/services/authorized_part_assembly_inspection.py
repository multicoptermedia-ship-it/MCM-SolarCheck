"""Read-only verification using expected integrity from an owner-scoped transfer record."""
from __future__ import annotations

from mcm_solarcheck.services.immutable_part_assembly_verifier import ImmutablePartAssemblyVerifier


class AuthorizedPartAssemblyInspection:
    def __init__(self, transfers, parts, remote, *, chunk_size: int = 1024 * 1024):
        self.transfers = transfers
        self.assembly = ImmutablePartAssemblyVerifier(parts, remote, chunk_size=chunk_size)

    def inspect(self, transfer_id: str, customer_id: str, project_id: str, *, expected_parts: int):
        record = self.transfers.get(transfer_id, customer_id, project_id)
        if record is None:
            raise PermissionError("transfer not found for owner")
        if record["state"] not in ("pending", "verified"):
            return "not_inspectable"
        return self.assembly.inspect(
            transfer_id, customer_id, project_id, expected_parts=expected_parts,
            expected_size=record["expected_size"],
            expected_sha256=record["expected_sha256"],
        )
