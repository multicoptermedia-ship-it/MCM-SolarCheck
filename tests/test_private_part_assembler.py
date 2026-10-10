from hashlib import sha256

from mcm_solarcheck.infrastructure.sqlite_immutable_part_manifest import SQLiteImmutablePartManifest
from mcm_solarcheck.services.private_part_assembler import PrivatePartAssembler


class Remote:
    def __init__(self, files):
        self.files = files

    def read_part_chunks(self, key, chunk_size):
        value = self.files[key]
        for offset in range(0, len(value), chunk_size):
            yield value[offset:offset + chunk_size]


def test_streamed_private_assembly_matches_original_file(tmp_path):
    manifest = SQLiteImmutablePartManifest(tmp_path / "parts.db")
    transfer = "a" * 32
    remote = {}
    for index, part in enumerate((b"abc", b"def", b"ghi")):
        key = manifest.record(transfer, "c", "p", index, sha256(part).hexdigest(), len(part))
        remote[key] = part
    directory = tmp_path / "private"
    directory.mkdir()
    assembled = PrivatePartAssembler(manifest, Remote(remote), chunk_size=2).assemble(
        transfer, "c", "p", expected_parts=3, expected_size=9,
        expected_sha256=sha256(b"abcdefghi").hexdigest(), directory=directory
    )
    assert assembled.parent == directory
    assert assembled.name.startswith(".assembly-")
    assert assembled.read_bytes() == b"abcdefghi"
