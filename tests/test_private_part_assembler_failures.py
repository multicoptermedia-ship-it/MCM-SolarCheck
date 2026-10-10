from hashlib import sha256

import pytest

from mcm_solarcheck.infrastructure.sqlite_immutable_part_manifest import SQLiteImmutablePartManifest
from mcm_solarcheck.services.private_part_assembler import PrivatePartAssembler


class Remote:
    def __init__(self, content):
        self.content = content

    def read_part_chunks(self, key, chunk_size):
        if self.content is None:
            raise OSError("remote missing")
        yield self.content


@pytest.mark.parametrize("content", [b"abd", b"ab", b"abcd", b"", None])
def test_failed_assembly_leaves_no_temporary_file(tmp_path, content):
    manifest = SQLiteImmutablePartManifest(tmp_path / "parts.db")
    transfer = "a" * 32
    manifest.record(transfer, "c", "p", 0, sha256(b"abc").hexdigest(), 3)
    directory = tmp_path / "private"
    directory.mkdir()
    with pytest.raises((ValueError, OSError)):
        PrivatePartAssembler(manifest, Remote(content), chunk_size=8).assemble(
            transfer, "c", "p", expected_parts=1, expected_size=3,
            expected_sha256=sha256(b"abc").hexdigest(), directory=directory
        )
    assert list(directory.iterdir()) == []


def test_cross_customer_cannot_assemble(tmp_path):
    manifest = SQLiteImmutablePartManifest(tmp_path / "parts.db")
    transfer = "a" * 32
    manifest.record(transfer, "c", "p", 0, sha256(b"abc").hexdigest(), 3)
    directory = tmp_path / "private"
    directory.mkdir()
    with pytest.raises(ValueError):
        PrivatePartAssembler(manifest, Remote(b"abc")).assemble(
            transfer, "other", "p", expected_parts=1, expected_size=3,
            expected_sha256=sha256(b"abc").hexdigest(), directory=directory
        )
    assert list(directory.iterdir()) == []
