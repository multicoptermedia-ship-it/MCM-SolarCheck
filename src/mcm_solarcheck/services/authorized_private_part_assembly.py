"""Owner-scoped private assembly using integrity from canonical transfer metadata."""
from __future__ import annotations

from mcm_solarcheck.services.private_part_assembler import PrivatePartAssembler


class AuthorizedPrivatePartAssembly:
    def __init__(self, transfers, parts, remote, *, chunk_size: int = 1024 * 1024):
        self.transfers = transfers
        self.assembler = PrivatePartAssembler(parts, remote, chunk_size=chunk_size)

    def assemble(self, transfer_id: str, customer_id: str, project_id: str,
                 *, expected_parts: int, directory):
        record = self.transfers.get(transfer_id, customer_id, project_id)
        if record is None:
            raise PermissionError("transfer not found for owner")
        if record["state"] != "pending":
            raise ValueError("transfer not pending")
        return self.assembler.assemble(
            transfer_id, customer_id, project_id,
            expected_parts=expected_parts, expected_size=record["expected_size"],
            expected_sha256=record["expected_sha256"], directory=directory,
        )
