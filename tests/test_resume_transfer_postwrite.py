from contextlib import contextmanager
from hashlib import sha256
from io import BytesIO

from mcm_solarcheck.infrastructure.sqlite_transfer_manifest import SQLiteTransferManifest
from mcm_solarcheck.services.resume_transfer_coordinator import ResumeTransferCoordinator


class Locks:
    @contextmanager
    def hold(self, *parts):
        yield


class NoAppendRemote:
    def __init__(self, content):
        self.content = content

    def read_staging_chunks(self, key, chunk_size):
        for i in range(0, len(self.content), chunk_size):
            yield self.content[i:i + chunk_size]


class CorruptingRemote(NoAppendRemote):
    def append_chunks_if_size(self, key, expected_offset, chunks):
        assert len(self.content) == expected_offset
        self.content += b"X" * sum(len(chunk) for chunk in chunks)


def make(tmp_path):
    store = SQLiteTransferManifest(tmp_path / "db.sqlite")
    transfer = store.create("c", "p", "c/p/image.jpg", 6, sha256(b"abcdef").hexdigest())
    return store, transfer


def test_missing_conditional_append_capability_fails_closed(tmp_path):
    store, transfer = make(tmp_path)
    outcome = ResumeTransferCoordinator(store, NoAppendRemote(b"abc"), locks=Locks()).resume(
        transfer, "c", "p", BytesIO(b"abcdef")
    )
    assert outcome == "append_unsupported"
    assert store.get(transfer, "c", "p")["state"] == "pending"


def test_remote_corruption_after_append_prevents_verified_state(tmp_path):
    store, transfer = make(tmp_path)
    outcome = ResumeTransferCoordinator(store, CorruptingRemote(b"abc"), locks=Locks()).resume(
        transfer, "c", "p", BytesIO(b"abcdef")
    )
    assert outcome == "hash_mismatch"
    assert store.get(transfer, "c", "p")["state"] == "pending"
