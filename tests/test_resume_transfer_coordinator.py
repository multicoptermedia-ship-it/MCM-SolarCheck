from contextlib import contextmanager
from hashlib import sha256
from io import BytesIO

from mcm_solarcheck.infrastructure.sqlite_transfer_manifest import SQLiteTransferManifest
from mcm_solarcheck.services.resume_transfer_coordinator import ResumeTransferCoordinator


class Locks:
    @contextmanager
    def hold(self, *parts):
        yield


class Remote:
    def __init__(self, content):
        self.content = content
        self.append_calls = 0

    def read_staging_chunks(self, key, chunk_size):
        for i in range(0, len(self.content), chunk_size):
            yield self.content[i:i + chunk_size]

    def append_chunks_if_size(self, key, expected_offset, chunks):
        self.append_calls += 1
        if len(self.content) != expected_offset:
            raise RuntimeError("remote offset changed")
        self.content += b"".join(chunks)


def test_resume_appends_only_missing_bytes_and_verifies(tmp_path):
    store = SQLiteTransferManifest(tmp_path / "db.sqlite")
    transfer = store.create("c", "p", "c/p/rgb.jpg", 6, sha256(b"abcdef").hexdigest())
    remote = Remote(b"abc")
    source = BytesIO(b"abcdef")
    source.seek(2)
    outcome = ResumeTransferCoordinator(store, remote, locks=Locks(), chunk_size=2).resume(
        transfer, "c", "p", source
    )
    assert outcome == "verified"
    assert remote.content == b"abcdef"
    assert remote.append_calls == 1
    assert source.tell() == 2
    assert store.get(transfer, "c", "p")["state"] == "verified"


def test_complete_staging_needs_no_append(tmp_path):
    store = SQLiteTransferManifest(tmp_path / "db.sqlite")
    transfer = store.create("c", "p", "c/p/rgb.jpg", 6, sha256(b"abcdef").hexdigest())
    remote = Remote(b"abcdef")
    assert ResumeTransferCoordinator(store, remote, locks=Locks()).resume(
        transfer, "c", "p", BytesIO(b"abcdef")
    ) == "verified"
    assert remote.append_calls == 0
