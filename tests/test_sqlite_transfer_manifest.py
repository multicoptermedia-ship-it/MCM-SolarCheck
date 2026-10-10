from hashlib import sha256

import pytest

from mcm_solarcheck.infrastructure.sqlite_transfer_manifest import SQLiteTransferManifest


def test_manifest_persists_across_instances_and_enforces_owner(tmp_path):
    database = tmp_path / "transfers.db"
    store = SQLiteTransferManifest(database)
    transfer = store.create("alice", "project", "alice/project/image.jpg", 3, sha256(b"rgb").hexdigest())
    reopened = SQLiteTransferManifest(database)
    row = reopened.get(transfer, "alice", "project")
    assert row["state"] == "pending"
    assert row["staging_key"] == ".staging/" + transfer
    assert reopened.get(transfer, "bob", "project") is None
    assert not reopened.transition(transfer, "bob", "project", "pending", "verified")


def test_manifest_transitions_are_conditional(tmp_path):
    store = SQLiteTransferManifest(tmp_path / "transfers.db")
    transfer = store.create("c", "p", "c/p/image.jpg", 3, sha256(b"rgb").hexdigest())
    assert store.transition(transfer, "c", "p", "pending", "verified")
    assert not store.transition(transfer, "c", "p", "pending", "verified")
    assert store.transition(transfer, "c", "p", "verified", "published")
    assert not store.transition(transfer, "c", "p", "verified", "aborted")
    with pytest.raises(ValueError):
        store.transition(transfer, "c", "p", "published", "pending")


@pytest.mark.parametrize("key", ["../escape", "/absolute", "a//b", ".staging/hidden"])
def test_manifest_rejects_unsafe_final_keys(tmp_path, key):
    store = SQLiteTransferManifest(tmp_path / "transfers.db")
    with pytest.raises(ValueError):
        store.create("c", "p", key, 3, sha256(b"rgb").hexdigest())
