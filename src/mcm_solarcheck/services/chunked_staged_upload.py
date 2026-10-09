"""Bounded-memory staged upload using transport-provided chunk iterators.

This service does not resume interrupted uploads; staging IDs are per attempt.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import BinaryIO, Iterable, Protocol
from uuid import uuid4


class ChunkedUploadBackend(Protocol):
    def write_staging_chunks(self, key: str, chunks: Iterable[bytes]) -> None: ...
    def read_staging_chunks(self, key: str, chunk_size: int) -> Iterable[bytes]: ...
    def publish(self, staging_key: str, final_key: str) -> None: ...
    def remove_staging(self, key: str) -> None: ...


@dataclass(frozen=True)
class ChunkedDeliveryReceipt:
    final_key: str
    size_bytes: int
    sha256_hex: str


class ChunkedStagedUploadDelivery:
    def __init__(self, backend: ChunkedUploadBackend, *, chunk_size: int = 1024 * 1024):
        if type(chunk_size) is not int or chunk_size <= 0:
            raise ValueError("chunk_size must be a positive integer")
        self.backend = backend
        self.chunk_size = chunk_size

    def deliver(self, final_key: str, source: BinaryIO) -> ChunkedDeliveryReceipt:
        if not isinstance(final_key, str) or not final_key or final_key.startswith("/") or any(
            part in ("", ".", "..") for part in final_key.split("/")
        ) or chr(92) in final_key or chr(0) in final_key or final_key.startswith(".staging/"):
            raise ValueError("invalid final key")
        key = ".staging/" + uuid4().hex
        expected_hash = sha256()
        total = 0

        def chunks():
            nonlocal total
            while True:
                block = source.read(self.chunk_size)
                if not block:
                    return
                if not isinstance(block, bytes) or len(block) > self.chunk_size:
                    raise ValueError("source must yield bounded bytes")
                total += len(block)
                expected_hash.update(block)
                yield block

        try:
            self.backend.write_staging_chunks(key, chunks())
            if total == 0:
                raise ValueError("empty upload")
            actual_hash = sha256()
            actual_size = 0
            for block in self.backend.read_staging_chunks(key, self.chunk_size):
                if not isinstance(block, bytes) or len(block) > self.chunk_size:
                    raise ValueError("backend yielded unbounded chunk")
                actual_hash.update(block)
                actual_size += len(block)
                if actual_size > total:
                    raise ValueError("staged upload integrity mismatch")
            if actual_size != total or actual_hash.digest() != expected_hash.digest():
                raise ValueError("staged upload integrity mismatch")
            self.backend.publish(key, final_key)
        finally:
            self.backend.remove_staging(key)
        return ChunkedDeliveryReceipt(final_key, total, expected_hash.hexdigest())
