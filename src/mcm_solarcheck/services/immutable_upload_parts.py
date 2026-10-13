"""Immutable upload-part naming and validation, independent of transport."""
from __future__ import annotations

import re

_ID = re.compile(r"^[a-f0-9]{32}$")
_DIGEST = re.compile(r"^[a-f0-9]{64}$")


def immutable_part_key(transfer_id: str, part_number: int, digest: str) -> str:
    if not isinstance(transfer_id, str) or not _ID.fullmatch(transfer_id):
        raise ValueError("invalid transfer id")
    if type(part_number) is not int or not 0 <= part_number < 1000000:
        raise ValueError("invalid part number")
    if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
        raise ValueError("invalid SHA-256")
    return f".staging/parts/{transfer_id}/{part_number:06d}-{digest}"


def validate_part_bytes(data: bytes, expected_digest: str, *, max_part_bytes: int = 8 * 1024 * 1024) -> None:
    from hashlib import sha256
    if type(max_part_bytes) is not int or max_part_bytes <= 0:
        raise ValueError("invalid part limit")
    if not isinstance(data, bytes) or not data or len(data) > max_part_bytes:
        raise ValueError("invalid part bytes")
    if not isinstance(expected_digest, str) or not _DIGEST.fullmatch(expected_digest):
        raise ValueError("invalid SHA-256")
    if sha256(data).hexdigest() != expected_digest:
        raise ValueError("part digest mismatch")
