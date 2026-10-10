from hashlib import sha256
from io import BytesIO

from mcm_solarcheck.infrastructure.sqlite_transfer_manifest import SQLiteTransferManifest
from mcm_solarcheck.services.resume_preflight import ResumePreflight


class Remote:
    def __init__(self, content):
        self.content = content
        self.reads = 0

    def read_staging_chunks(self, key, chunk_size):
        self.reads += 1
        for start in range(0, len(self.content), chunk_size):
            yield self.content[start:start + chunk_size]


def test_preflight_verifies_source_and_prefix(tmp_path):
    store = SQLiteTransferManifest(tmp_path / "manifest.db")
    transfer = store.create("c", "p", "c/p/file.jpg", 6, sha256(b"abcdef").hexdigest())
    source = BytesIO(b"abcdef")
    source.seek(2)
    result = ResumePreflight(store, Remote(b"abcd"), chunk_size=2).check(transfer, "c", "p", source)
    assert (result.status, result.verified_offset) == ("verified_prefix", 4)
    assert source.tell() == 2
    assert store.get(transfer, "c", "p")["state"] == "pending"


def test_changed_source_prevents_remote_inspection(tmp_path):
    store = SQLiteTransferManifest(tmp_path / "manifest.db")
    transfer = store.create("c", "p", "c/p/file.jpg", 6, sha256(b"abcdef").hexdigest())
    remote = Remote(b"abcd")
    result = ResumePreflight(store, remote).check(transfer, "c", "p", BytesIO(b"abcxef"))
    assert result.status == "source_mismatch"
    assert remote.reads == 0
