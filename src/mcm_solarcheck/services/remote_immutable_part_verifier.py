"""Read-only streaming verification of immutable remote parts."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from mcm_solarcheck.services.immutable_upload_parts import immutable_part_key


@dataclass(frozen=True)
class RemotePartInspection:
    status: str
    verified_parts: int = 0
    verified_bytes: int = 0


class RemoteImmutablePartVerifier:
    def __init__(self, manifest, remote, *, chunk_size: int = 1024 * 1024):
        if type(chunk_size) is not int or chunk_size <= 0:
            raise ValueError("invalid chunk size")
        self.manifest = manifest
        self.remote = remote
        self.chunk_size = chunk_size

    def inspect(self, transfer_id: str, customer_id: str, project_id: str,
                *, expected_parts: int, expected_size: int) -> RemotePartInspection:
        if type(expected_parts) is not int or expected_parts <= 0:
            raise ValueError("invalid part count")
        if type(expected_size) is not int or expected_size <= 0:
            raise ValueError("invalid expected size")
        rows = self.manifest.list_parts(transfer_id, customer_id, project_id)
        if len(rows) != expected_parts or [r["part_number"] for r in rows] != list(range(expected_parts)):
            return RemotePartInspection("incomplete_metadata")
        if sum(r["size"] for r in rows) != expected_size:
            return RemotePartInspection("size_mismatch")
        verified = 0
        total = 0
        for row in rows:
            try:
                expected_key = immutable_part_key(transfer_id, row["part_number"], row["sha256"])
                if row["storage_key"] != expected_key:
                    return RemotePartInspection("invalid_key", verified, total)
                digest = sha256()
                part_size = 0
                for chunk in self.remote.read_part_chunks(expected_key, self.chunk_size):
                    if not isinstance(chunk, bytes) or not chunk or len(chunk) > self.chunk_size:
                        return RemotePartInspection("unsafe_chunk", verified, total)
                    part_size += len(chunk)
                    if part_size > row["size"]:
                        return RemotePartInspection("size_mismatch", verified, total)
                    digest.update(chunk)
                if part_size != row["size"]:
                    return RemotePartInspection("size_mismatch", verified, total)
                if digest.hexdigest() != row["sha256"]:
                    return RemotePartInspection("hash_mismatch", verified, total)
            except (OSError, IOError, KeyError, ValueError):
                return RemotePartInspection("unavailable", verified, total)
            verified += 1
            total += part_size
        return RemotePartInspection("verified_parts", verified, total)
