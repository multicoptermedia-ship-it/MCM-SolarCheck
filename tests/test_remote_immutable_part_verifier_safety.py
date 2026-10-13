from hashlib import sha256

import pytest

from mcm_solarcheck.infrastructure.sqlite_immutable_part_manifest import SQLiteImmutablePartManifest
from mcm_solarcheck.services.remote_immutable_part_verifier import RemoteImmutablePartVerifier


class Remote:
    def __init__(self, content):
        self.content = content

    def read_part_chunks(self, key, chunk_size):
        if self.content is None:
            raise OSError("unavailable")
        yield self.content


@pytest.mark.parametrize("content,expected", [
    (b"abd", "hash_mismatch"),
    (b"ab", "size_mismatch"),
    (b"abcd", "size_mismatch"),
    (None, "unavailable"),
    (b"", "unsafe_chunk"),
])
def test_corrupt_or_missing_remote_part_fails_closed(tmp_path, content, expected):
    manifest = SQLiteImmutablePartManifest(tmp_path / "parts.db")
    transfer = "a" * 32
    manifest.record(transfer, "c", "p", 0, sha256(b"abc").hexdigest(), 3)
    result = RemoteImmutablePartVerifier(manifest, Remote(content), chunk_size=8).inspect(
        transfer, "c", "p", expected_parts=1, expected_size=3
    )
    assert result.status == expected
    assert result.verified_parts == 0


def test_cross_customer_has_no_remote_reads(tmp_path):
    manifest = SQLiteImmutablePartManifest(tmp_path / "parts.db")
    transfer = "a" * 32
    manifest.record(transfer, "c", "p", 0, sha256(b"abc").hexdigest(), 3)
    result = RemoteImmutablePartVerifier(manifest, Remote(b"abc")).inspect(
        transfer, "other", "p", expected_parts=1, expected_size=3
    )
    assert result.status == "incomplete_metadata"
