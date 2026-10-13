from hashlib import sha256
from io import BytesIO

import pytest

from mcm_solarcheck.services.chunked_staged_upload import ChunkedStagedUploadDelivery


class MemoryChunkedBackend:
    def __init__(self):
        self.files = {}
        self.writes = []

    def write_staging_chunks(self, key, chunks):
        blocks = []
        for block in chunks:
            self.writes.append(len(block))
            blocks.append(block)
        self.files[key] = b"".join(blocks)

    def read_staging_chunks(self, key, chunk_size):
        data = self.files[key]
        for offset in range(0, len(data), chunk_size):
            yield data[offset:offset + chunk_size]

    def publish(self, source, destination):
        if destination in self.files:
            raise FileExistsError(destination)
        self.files[destination] = self.files[source]

    def remove_staging(self, key):
        self.files.pop(key, None)


def test_chunked_delivery_checks_integrity_and_bounds():
    backend = MemoryChunkedBackend()
    receipt = ChunkedStagedUploadDelivery(backend, chunk_size=7).deliver(
        "customer/project/rgb.jpg", BytesIO(b"abc" * 100)
    )
    assert receipt.size_bytes == 300
    assert receipt.sha256_hex == sha256(b"abc" * 100).hexdigest()
    assert max(backend.writes) <= 7
    assert backend.files == {"customer/project/rgb.jpg": b"abc" * 100}


def test_empty_upload_rejected_and_staging_removed():
    backend = MemoryChunkedBackend()
    with pytest.raises(ValueError, match="empty"):
        ChunkedStagedUploadDelivery(backend).deliver("c/p/image.jpg", BytesIO(b""))
    assert backend.files == {}
