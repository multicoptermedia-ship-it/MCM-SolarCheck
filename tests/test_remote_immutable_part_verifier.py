from hashlib import sha256

from mcm_solarcheck.infrastructure.sqlite_immutable_part_manifest import SQLiteImmutablePartManifest
from mcm_solarcheck.services.remote_immutable_part_verifier import RemoteImmutablePartVerifier


class Remote:
    def __init__(self, data):
        self.data = data
        self.reads = 0

    def read_part_chunks(self, key, chunk_size):
        self.reads += 1
        for i in range(0, len(self.data[key]), chunk_size):
            yield self.data[key][i:i + chunk_size]


def test_verified_parts_are_read_back_in_order(tmp_path):
    manifest = SQLiteImmutablePartManifest(tmp_path / "parts.db")
    transfer = "a" * 32
    data = {}
    for i, value in enumerate((b"abc", b"def")):
        key = manifest.record(transfer, "c", "p", i, sha256(value).hexdigest(), len(value))
        data[key] = value
    remote = Remote(data)
    result = RemoteImmutablePartVerifier(manifest, remote, chunk_size=2).inspect(
        transfer, "c", "p", expected_parts=2, expected_size=6
    )
    assert (result.status, result.verified_parts, result.verified_bytes) == ("verified_parts", 2, 6)
    assert remote.reads == 2


def test_incomplete_metadata_does_not_read_remote(tmp_path):
    manifest = SQLiteImmutablePartManifest(tmp_path / "parts.db")
    remote = Remote({})
    result = RemoteImmutablePartVerifier(manifest, remote).inspect(
        "a" * 32, "c", "p", expected_parts=1, expected_size=3
    )
    assert result.status == "incomplete_metadata"
    assert remote.reads == 0
