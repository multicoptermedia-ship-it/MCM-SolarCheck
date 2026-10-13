from contextlib import contextmanager
from hashlib import sha256
from io import BytesIO

import pytest

from mcm_solarcheck.infrastructure.sqlite_transfer_manifest import SQLiteTransferManifest
from mcm_solarcheck.services.resume_transfer_coordinator import ResumeTransferCoordinator


class Locks:
    @contextmanager
    def hold(self, *parts):
        yield


class Remote:
    def __init__(self, content):
        self.content = content
        self.appended = False

    def read_staging_chunks(self, key, chunk_size):
        for i in range(0, len(self.content), chunk_size):
            yield self.content[i:i + chunk_size]

    def append_chunks_if_size(self, key, expected_offset, chunks):
        self.appended = True
        if len(self.content) != expected_offset:
            raise RuntimeError("stale offset")
        self.content += b"".join(chunks)


def setup(tmp_path, content=b"abc"):
    store = SQLiteTransferManifest(tmp_path / "db.sqlite")
    transfer = store.create("c", "p", "c/p/rgb.jpg", 6, sha256(b"abcdef").hexdigest())
    return store, transfer, Remote(content)


def test_corrupted_prefix_is_not_appended(tmp_path):
    store, transfer, remote = setup(tmp_path, b"abX")
    result = ResumeTransferCoordinator(store, remote, locks=Locks()).resume(
        transfer, "c", "p", BytesIO(b"abcdef")
    )
    assert result == "prefix_mismatch"
    assert not remote.appended
    assert store.get(transfer, "c", "p")["state"] == "pending"


def test_changed_source_is_not_appended(tmp_path):
    store, transfer, remote = setup(tmp_path)
    result = ResumeTransferCoordinator(store, remote, locks=Locks()).resume(
        transfer, "c", "p", BytesIO(b"abcxef")
    )
    assert result == "source_mismatch"
    assert not remote.appended


def test_cross_customer_denied(tmp_path):
    store, transfer, remote = setup(tmp_path)
    with pytest.raises(PermissionError):
        ResumeTransferCoordinator(store, remote, locks=Locks()).resume(
            transfer, "other", "p", BytesIO(b"abcdef")
        )
    assert not remote.appended


def test_missing_lock_provider_is_rejected(tmp_path):
    store, transfer, remote = setup(tmp_path)
    with pytest.raises(ValueError):
        ResumeTransferCoordinator(store, remote, locks=None)
