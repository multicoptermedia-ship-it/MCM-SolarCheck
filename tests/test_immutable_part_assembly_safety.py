from hashlib import sha256

import pytest

from mcm_solarcheck.infrastructure.sqlite_immutable_part_manifest import SQLiteImmutablePartManifest
from mcm_solarcheck.services.immutable_part_assembly_verifier import ImmutablePartAssemblyVerifier


class Remote:
    def __init__(self, content):
        self.content = content

    def read_part_chunks(self, key, chunk_size):
        if self.content is None:
            raise OSError("missing")
        yield self.content


@pytest.mark.parametrize("content,status", [
    (b"abd", "part_hash_mismatch"),
    (b"ab", "size_mismatch"),
    (b"abcd", "size_mismatch"),
    (b"", "unsafe_chunk"),
    (None, "unavailable"),
])
def test_bad_remote_part_prevents_full_file_verification(tmp_path, content, status):
    manifest = SQLiteImmutablePartManifest(tmp_path / "parts.db")
    transfer = "a" * 32
    manifest.record(transfer, "c", "p", 0, sha256(b"abc").hexdigest(), 3)
    outcome = ImmutablePartAssemblyVerifier(manifest, Remote(content), chunk_size=8).inspect(
        transfer, "c", "p", expected_parts=1, expected_size=3,
        expected_sha256=sha256(b"abc").hexdigest()
    )
    assert outcome.status == status


def test_wrong_owner_cannot_inspect_part_contents(tmp_path):
    manifest = SQLiteImmutablePartManifest(tmp_path / "parts.db")
    transfer = "a" * 32
    manifest.record(transfer, "c", "p", 0, sha256(b"abc").hexdigest(), 3)
    outcome = ImmutablePartAssemblyVerifier(manifest, Remote(b"abc")).inspect(
        transfer, "other", "p", expected_parts=1, expected_size=3,
        expected_sha256=sha256(b"abc").hexdigest()
    )
    assert outcome.status == "incomplete_metadata"
