"""Opt-in immutable-part writer; requires exclusive create on storage backend."""
from __future__ import annotations

from hashlib import sha256

from mcm_solarcheck.services.immutable_upload_parts import (
    immutable_part_key,
    validate_part_bytes,
)


class ImmutablePartWriter:
    def __init__(self, remote, *, max_part_bytes: int = 8 * 1024 * 1024):
        if type(max_part_bytes) is not int or max_part_bytes <= 0:
            raise ValueError("invalid part limit")
        self.remote = remote
        self.max_part_bytes = max_part_bytes

    def write(self, transfer_id: str, part_number: int, data: bytes) -> tuple[str, str]:
        if not isinstance(data, bytes):
            raise ValueError("part must be bytes")
        digest = sha256(data).hexdigest()
        validate_part_bytes(data, digest, max_part_bytes=self.max_part_bytes)
        key = immutable_part_key(transfer_id, part_number, digest)
        create = getattr(self.remote, "write_exclusive", None)
        read = getattr(self.remote, "read", None)
        if not callable(create) or not callable(read):
            raise RuntimeError("backend lacks exclusive create or readback")
        try:
            create(key, data)
        except FileExistsError:
            # Retry is safe only when existing immutable content is identical.
            pass
        actual = read(key)
        validate_part_bytes(actual, digest, max_part_bytes=self.max_part_bytes)
        if actual != data:
            raise ValueError("remote part differs")
        return key, digest
