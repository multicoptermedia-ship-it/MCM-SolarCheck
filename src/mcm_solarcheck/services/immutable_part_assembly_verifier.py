"""Read-only streaming reconstruction and full-file verification of immutable parts."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from mcm_solarcheck.services.immutable_upload_parts import immutable_part_key


@dataclass(frozen=True)
class AssemblyInspection:
    status: str
    verified_parts: int = 0
    verified_bytes: int = 0


class ImmutablePartAssemblyVerifier:
    def __init__(self, manifest, remote, *, chunk_size: int = 1024 * 1024):
        if type(chunk_size) is not int or chunk_size <= 0:
            raise ValueError("invalid chunk size")
        self.manifest = manifest
        self.remote = remote
        self.chunk_size = chunk_size

    def inspect(self, transfer_id: str, customer_id: str, project_id: str,
                *, expected_parts: int, expected_size: int,
                expected_sha256: str) -> AssemblyInspection:
        if type(expected_parts) is not int or expected_parts <= 0:
            raise ValueError("invalid part count")
        if type(expected_size) is not int or expected_size <= 0:
            raise ValueError("invalid size")
        if (not isinstance(expected_sha256, str) or len(expected_sha256) != 64
                or any(ch not in "0123456789abcdef" for ch in expected_sha256)):
            raise ValueError("invalid SHA-256")
        rows = self.manifest.list_parts(transfer_id, customer_id, project_id)
        if len(rows) != expected_parts or [r["part_number"] for r in rows] != list(range(expected_parts)):
            return AssemblyInspection("incomplete_metadata")
        if sum(r["size"] for r in rows) != expected_size:
            return AssemblyInspection("size_mismatch")
        overall = sha256()
        verified = 0
        total = 0
        for row in rows:
            try:
                key = immutable_part_key(transfer_id, row["part_number"], row["sha256"])
                if key != row["storage_key"]:
                    return AssemblyInspection("invalid_key", verified, total)
                part_hash = sha256()
                part_size = 0
                for block in self.remote.read_part_chunks(key, self.chunk_size):
                    if not isinstance(block, bytes) or not block or len(block) > self.chunk_size:
                        return AssemblyInspection("unsafe_chunk", verified, total)
                    part_size += len(block)
                    if part_size > row["size"]:
                        return AssemblyInspection("size_mismatch", verified, total)
                    part_hash.update(block)
                    overall.update(block)
                if part_size != row["size"]:
                    return AssemblyInspection("size_mismatch", verified, total)
                if part_hash.hexdigest() != row["sha256"]:
                    return AssemblyInspection("part_hash_mismatch", verified, total)
            except (OSError, IOError, KeyError, ValueError):
                return AssemblyInspection("unavailable", verified, total)
            verified += 1
            total += part_size
        if total != expected_size:
            return AssemblyInspection("size_mismatch", verified, total)
        if overall.hexdigest() != expected_sha256:
            return AssemblyInspection("file_hash_mismatch", verified, total)
        return AssemblyInspection("verified_file", verified, total)
