"""Provider-neutral staged delivery: never publish before integrity verification."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol
from uuid import uuid4


class StagedUploadBackend(Protocol):
    def put_staging(self, key: str, data: bytes) -> None: ...
    def read_staging(self, key: str) -> bytes: ...
    def publish(self, staging_key: str, final_key: str) -> None: ...
    def remove_staging(self, key: str) -> None: ...


@dataclass(frozen=True)
class DeliveryReceipt:
    final_key: str
    size_bytes: int
    sha256_hex: str


class StagedUploadDelivery:
    def __init__(self, backend: StagedUploadBackend):
        self.backend = backend

    def deliver(self, final_key: str, data: bytes) -> DeliveryReceipt:
        if not final_key or final_key.startswith("/") or any(
            part in ("", ".", "..") for part in final_key.split("/")
        ) or chr(92) in final_key or chr(0) in final_key:
            raise ValueError("invalid final key")
        if not isinstance(data, bytes) or not data:
            raise ValueError("nonempty bytes required")
        staging_key = ".staging/" + uuid4().hex
        expected = sha256(data).hexdigest()
        self.backend.put_staging(staging_key, data)
        try:
            received = self.backend.read_staging(staging_key)
            if len(received) != len(data) or sha256(received).hexdigest() != expected:
                raise ValueError("staged upload integrity mismatch")
            self.backend.publish(staging_key, final_key)
        finally:
            self.backend.remove_staging(staging_key)
        return DeliveryReceipt(final_key, len(data), expected)
