"""Chunked SFTP adapter, relying on injected exclusive remote operations."""
from __future__ import annotations

from typing import Iterable

from mcm_solarcheck.infrastructure.sftp_staged_upload_backend import SFTPStagedUploadBackend


class ChunkedSFTPStagedUploadBackend(SFTPStagedUploadBackend):
    def write_staging_chunks(self, key: str, chunks: Iterable[bytes]) -> None:
        if not key.startswith(".staging/"):
            raise ValueError("staging key required")
        method = getattr(self.transport, "write_exclusive_chunks", None)
        if not callable(method):
            raise NotImplementedError("SFTP transport must support exclusive chunked writes")
        method(self._remote(key), chunks)

    def read_staging_chunks(self, key: str, chunk_size: int) -> Iterable[bytes]:
        if not key.startswith(".staging/"):
            raise ValueError("staging key required")
        method = getattr(self.transport, "read_chunks", None)
        if not callable(method):
            raise NotImplementedError("SFTP transport must support chunked reads")
        return method(self._remote(key), chunk_size)
