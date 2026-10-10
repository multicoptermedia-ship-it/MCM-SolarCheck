"""Strict resume-read adapter for injected SFTP streaming transports.

Read-only: does not open a network connection or append remote bytes.
"""
from __future__ import annotations

from mcm_solarcheck.infrastructure.chunked_sftp_staged_backend import ChunkedSFTPStagedUploadBackend


class ReadOnlySFTPResumeBackend:
    def __init__(self, transport, *, root: str):
        self.backend = ChunkedSFTPStagedUploadBackend(transport, root=root)

    def read_staging_chunks(self, key: str, chunk_size: int):
        if type(chunk_size) is not int or chunk_size <= 0:
            raise ValueError("invalid chunk size")
        return self.backend.read_staging_chunks(key, chunk_size)
