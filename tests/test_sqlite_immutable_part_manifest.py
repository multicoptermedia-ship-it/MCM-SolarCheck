from hashlib import sha256

import pytest

from mcm_solarcheck.infrastructure.sqlite_immutable_part_manifest import SQLiteImmutablePartManifest


def test_part_records_survive_restart_and_are_owner_scoped(tmp_path):
    db = tmp_path / "parts.db"
    manifest = SQLiteImmutablePartManifest(db)
    digest = sha256(b"abc").hexdigest()
    key = manifest.record("a" * 32, "customer", "project", 0, digest, 3)
    reopened = SQLiteImmutablePartManifest(db)
    assert reopened.list_parts("a" * 32, "customer", "project") == [{
        "part_number": 0, "sha256": digest, "size": 3, "storage_key": key
    }]
    assert reopened.list_parts("a" * 32, "other", "project") == []


def test_identical_retry_is_idempotent_but_conflict_is_rejected(tmp_path):
    manifest = SQLiteImmutablePartManifest(tmp_path / "parts.db")
    digest = sha256(b"abc").hexdigest()
    args = ("a" * 32, "customer", "project", 0, digest, 3)
    assert manifest.record(*args) == manifest.record(*args)
    with pytest.raises(ValueError):
        manifest.record("a" * 32, "customer", "project", 0, sha256(b"xyz").hexdigest(), 3)
    with pytest.raises(ValueError):
        manifest.record("a" * 32, "other", "project", 0, digest, 3)
