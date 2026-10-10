from hashlib import sha256

from mcm_solarcheck.infrastructure.sqlite_immutable_part_manifest import SQLiteImmutablePartManifest
from mcm_solarcheck.services.immutable_part_assembly_verifier import ImmutablePartAssemblyVerifier


class Remote:
    def __init__(self, data):
        self.data = data

    def read_part_chunks(self, key, chunk_size):
        value = self.data[key]
        for offset in range(0, len(value), chunk_size):
            yield value[offset:offset + chunk_size]


def test_full_file_verified_without_concatenating_into_memory(tmp_path):
    manifest = SQLiteImmutablePartManifest(tmp_path / "parts.db")
    transfer = "a" * 32
    remote_data = {}
    for index, part in enumerate((b"abc", b"defg", b"hij")):
        key = manifest.record(transfer, "c", "p", index, sha256(part).hexdigest(), len(part))
        remote_data[key] = part
    outcome = ImmutablePartAssemblyVerifier(manifest, Remote(remote_data), chunk_size=2).inspect(
        transfer, "c", "p", expected_parts=3, expected_size=10,
        expected_sha256=sha256(b"abcdefghij").hexdigest()
    )
    assert (outcome.status, outcome.verified_parts, outcome.verified_bytes) == ("verified_file", 3, 10)


def test_wrong_full_file_hash_is_rejected(tmp_path):
    manifest = SQLiteImmutablePartManifest(tmp_path / "parts.db")
    transfer = "a" * 32
    key = manifest.record(transfer, "c", "p", 0, sha256(b"abc").hexdigest(), 3)
    result = ImmutablePartAssemblyVerifier(manifest, Remote({key: b"abc"})).inspect(
        transfer, "c", "p", expected_parts=1, expected_size=3,
        expected_sha256=sha256(b"xyz").hexdigest()
    )
    assert result.status == "file_hash_mismatch"
