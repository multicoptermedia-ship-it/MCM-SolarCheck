"""Verify the entire local source before permitting a resume decision.

Requires a seekable source and restores the original stream position.
"""
from __future__ import annotations

from hashlib import sha256
from typing import BinaryIO


def verify_resume_source(source: BinaryIO, *, expected_size: int,
                         expected_sha256: str, chunk_size: int = 1024 * 1024) -> bool:
    if type(chunk_size) is not int or chunk_size <= 0:
        raise ValueError("invalid chunk size")
    if type(expected_size) is not int or expected_size <= 0:
        raise ValueError("invalid expected size")
    position = source.tell()
    digest = sha256()
    size = 0
    try:
        source.seek(0)
        while True:
            block = source.read(chunk_size)
            if not block:
                break
            if not isinstance(block, bytes) or len(block) > chunk_size:
                return False
            size += len(block)
            if size > expected_size:
                return False
            digest.update(block)
        return size == expected_size and digest.hexdigest() == expected_sha256
    finally:
        source.seek(position)
