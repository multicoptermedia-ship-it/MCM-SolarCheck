from hashlib import sha256
from io import BytesIO

import pytest

from mcm_solarcheck.infrastructure.sqlite_transfer_manifest import SQLiteTransferManifest
from mcm_solarcheck.services.resume_preflight import ResumePreflight


class Remote:
    def __init__(self, chunks):
        self.chunks = chunks

    def read_staging_chunks(self, key, chunk_size):
        yield from self.chunks


def setup(tmp_path):
    store = SQLiteTransferManifest(tmp_path / "manifest.db")
    transfer = store.create("owner", "project", "owner/project/file.jpg", 4, sha256(b"abcd").hexdigest())
    return store, transfer


def test_preflight_denies_cross_owner(tmp_path):
    store, transfer = setup(tmp_path)
    with pytest.raises(PermissionError):
        ResumePreflight(store, Remote([b"ab"])).check(transfer, "other", "project", BytesIO(b"abcd"))


def test_preflight_rejects_changed_remote_prefix(tmp_path):
    store, transfer = setup(tmp_path)
    result = ResumePreflight(store, Remote([b"ax"]), chunk_size=2).check(
        transfer, "owner", "project", BytesIO(b"abcd")
    )
    assert (result.status, result.verified_offset) == ("prefix_mismatch", 0)


def test_preflight_rejects_oversized_remote_chunk(tmp_path):
    store, transfer = setup(tmp_path)
    result = ResumePreflight(store, Remote([b"abc"]), chunk_size=2).check(
        transfer, "owner", "project", BytesIO(b"abcd")
    )
    assert (result.status, result.verified_offset) == ("unsafe_chunk", 0)


def test_preflight_refuses_completed_manifest(tmp_path):
    store, transfer = setup(tmp_path)
    assert store.transition(transfer, "owner", "project", "pending", "verified")
    result = ResumePreflight(store, Remote([b"ab"])).check(
        transfer, "owner", "project", BytesIO(b"abcd")
    )
    assert (result.status, result.verified_offset) == ("not_pending", 0)
