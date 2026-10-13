"""Read-only immutable part completeness inspection."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PartInventory:
    status: str
    count: int
    total_bytes: int


class ImmutablePartInventory:
    def __init__(self, manifest):
        self.manifest = manifest

    def inspect(self, transfer_id: str, customer_id: str, project_id: str,
                *, expected_parts: int, expected_size: int) -> PartInventory:
        if type(expected_parts) is not int or expected_parts <= 0:
            raise ValueError("invalid expected part count")
        if type(expected_size) is not int or expected_size <= 0:
            raise ValueError("invalid expected size")
        rows = self.manifest.list_parts(transfer_id, customer_id, project_id)
        total = sum(row["size"] for row in rows)
        numbers = [row["part_number"] for row in rows]
        if len(rows) > expected_parts or any(n >= expected_parts for n in numbers):
            status = "unexpected_parts"
        elif numbers != list(range(expected_parts)):
            status = "incomplete"
        elif total != expected_size:
            status = "size_mismatch"
        else:
            status = "complete_metadata"
        return PartInventory(status, len(rows), total)
