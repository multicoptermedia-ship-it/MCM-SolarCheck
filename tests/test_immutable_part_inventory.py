from hashlib import sha256

from mcm_solarcheck.infrastructure.sqlite_immutable_part_manifest import SQLiteImmutablePartManifest
from mcm_solarcheck.services.immutable_part_inventory import ImmutablePartInventory


def test_inventory_distinguishes_missing_and_complete_parts(tmp_path):
    manifest = SQLiteImmutablePartManifest(tmp_path / "parts.db")
    inventory = ImmutablePartInventory(manifest)
    transfer = "a" * 32
    assert inventory.inspect(transfer, "c", "p", expected_parts=2, expected_size=6).status == "incomplete"
    digest = sha256(b"abc").hexdigest()
    manifest.record(transfer, "c", "p", 0, digest, 3)
    assert inventory.inspect(transfer, "c", "p", expected_parts=2, expected_size=6).status == "incomplete"
    manifest.record(transfer, "c", "p", 1, digest, 3)
    result = inventory.inspect(transfer, "c", "p", expected_parts=2, expected_size=6)
    assert (result.status, result.count, result.total_bytes) == ("complete_metadata", 2, 6)
    assert inventory.inspect(transfer, "c", "p", expected_parts=2, expected_size=7).status == "size_mismatch"


def test_unexpected_part_numbers_are_rejected(tmp_path):
    manifest = SQLiteImmutablePartManifest(tmp_path / "parts.db")
    transfer = "b" * 32
    manifest.record(transfer, "c", "p", 2, sha256(b"abc").hexdigest(), 3)
    assert ImmutablePartInventory(manifest).inspect(
        transfer, "c", "p", expected_parts=2, expected_size=3
    ).status == "unexpected_parts"
