from hashlib import sha256
from io import BytesIO

from mcm_solarcheck.infrastructure.sqlite_transfer_manifest import SQLiteTransferManifest
from mcm_solarcheck.services.staged_resume_inspector import StagedResumeInspector


class Remote:
    def __init__(self, blocks):
        self.blocks = blocks

    def read_staging_chunks(self, key, chunk_size):
        yield from self.blocks


def setup(tmp_path):
    manifest = SQLiteTransferManifest(tmp_path / "db.sqlite")
    transfer = manifest.create("c", "p", "c/p/rgb.jpg", 4, sha256(b"abcd").hexdigest())
    return manifest, transfer


def test_unbounded_remote_block_fails_closed(tmp_path):
    manifest, transfer = setup(tmp_path)
    result = StagedResumeInspector(manifest, Remote([b"abcd"]), chunk_size=2).inspect(
        transfer, "c", "p", BytesIO(b"abcd")
    )
    assert (result.status, result.verified_offset) == ("unsafe_chunk", 0)


def test_short_source_does_not_authorize_offset(tmp_path):
    manifest, transfer = setup(tmp_path)
    result = StagedResumeInspector(manifest, Remote([b"abc"]), chunk_size=4).inspect(
        transfer, "c", "p", BytesIO(b"ab")
    )
    assert (result.status, result.verified_offset) == ("prefix_mismatch", 0)


def test_no_remote_bytes_returns_zero_offset(tmp_path):
    manifest, transfer = setup(tmp_path)
    result = StagedResumeInspector(manifest, Remote([])).inspect(
        transfer, "c", "p", BytesIO(b"abcd")
    )
    assert (result.status, result.verified_offset) == ("verified_prefix", 0)
