from io import BytesIO

import pytest

from mcm_solarcheck.services.chunked_staged_upload import ChunkedStagedUploadDelivery
from mcm_solarcheck.infrastructure.chunked_sftp_staged_backend import ChunkedSFTPStagedUploadBackend


class BrokenBackend:
    def __init__(self):
        self.files = {}
        self.published = False

    def write_staging_chunks(self, key, chunks):
        self.files[key] = b"".join(chunks)

    def read_staging_chunks(self, key, chunk_size):
        yield b"bad!"

    def publish(self, source, destination):
        self.published = True

    def remove_staging(self, key):
        self.files.pop(key, None)


def test_corrupted_remote_data_is_not_published():
    backend = BrokenBackend()
    with pytest.raises(ValueError, match="integrity mismatch"):
        ChunkedStagedUploadDelivery(backend, chunk_size=4).deliver(
            "c/p/thermal.tiff", BytesIO(b"original")
        )
    assert not backend.published
    assert backend.files == {}


class NoStreamingTransport:
    def remove(self, path):
        pass


def test_sftp_adapter_requires_chunked_transport_capability():
    backend = ChunkedSFTPStagedUploadBackend(NoStreamingTransport(), root="/private")
    with pytest.raises(NotImplementedError):
        ChunkedStagedUploadDelivery(backend).deliver("c/p/rgb.jpg", BytesIO(b"rgb"))


class OversizedBackend(BrokenBackend):
    def read_staging_chunks(self, key, chunk_size):
        yield b"x" * (chunk_size + 1)


def test_oversized_remote_chunk_is_rejected():
    backend = OversizedBackend()
    with pytest.raises(ValueError, match="unbounded chunk"):
        ChunkedStagedUploadDelivery(backend, chunk_size=4).deliver(
            "c/p/thermal.tiff", BytesIO(b"original")
        )
    assert not backend.published
    assert backend.files == {}
