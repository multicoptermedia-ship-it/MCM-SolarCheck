"""Adapter for chunk-readable remote part transports; no network connection created."""
from __future__ import annotations

from mcm_solarcheck.services.immutable_upload_parts import immutable_part_key


class ReadOnlyImmutablePartBackend:
    def __init__(self, transport):
        self.transport = transport

    def read_part_chunks(self, key: str, chunk_size: int):
        if type(chunk_size) is not int or chunk_size <= 0:
            raise ValueError("invalid chunk size")
        pieces = key.split("/")
        if len(pieces) != 4 or pieces[:2] != [".staging", "parts"]:
            raise ValueError("invalid immutable part path")
        transfer_id, part_name = pieces[2:]
        if len(part_name) != 71 or part_name[6] != "-":
            raise ValueError("invalid immutable part name")
        part_number = int(part_name[:6]) if part_name[:6].isdigit() else -1
        if immutable_part_key(transfer_id, part_number, part_name[7:]) != key:
            raise ValueError("noncanonical immutable part path")
        reader = getattr(self.transport, "read_part_chunks", None)
        if not callable(reader):
            raise RuntimeError("chunked part reads unsupported")
        return reader(key, chunk_size)
