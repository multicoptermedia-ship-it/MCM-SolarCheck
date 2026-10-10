from hashlib import sha256

import pytest

from mcm_solarcheck.infrastructure.sqlite_transfer_manifest import SQLiteTransferManifest
from mcm_solarcheck.services.staged_transfer_verifier import StagedTransferVerifier


class Remote:
    def __init__(self, content):
        self.content = content

    def read_staging_chunks(self, key, chunk_size):
        for start in range(0, len(self.content), chunk_size):
            yield self.content[start:start + chunk_size]


def test_verifier_checks_complete_remote_bytes(tmp_path):
    manifest = SQLiteTransferManifest(tmp_path / "db.sqlite")
    transfer = manifest.create("c", "p", "c/p/image.jpg", 3, sha256(b"rgb").hexdigest())
    assert StagedTransferVerifier(manifest, Remote(b"rgb"), chunk_size=2).inspect(transfer, "c", "p") == "verified_bytes"
    assert manifest.get(transfer, "c", "p")["state"] == "pending"


@pytest.mark.parametrize("content,expected", [
    (b"rbg", "hash_mismatch"),
    (b"rg", "size_mismatch"),
    (b"rgbx", "size_mismatch"),
])
def test_verifier_rejects_changed_remote_bytes(tmp_path, content, expected):
    manifest = SQLiteTransferManifest(tmp_path / "db.sqlite")
    transfer = manifest.create("c", "p", "c/p/image.jpg", 3, sha256(b"rgb").hexdigest())
    assert StagedTransferVerifier(manifest, Remote(content), chunk_size=2).inspect(transfer, "c", "p") == expected


def test_verifier_does_not_disclose_other_customers_transfer(tmp_path):
    manifest = SQLiteTransferManifest(tmp_path / "db.sqlite")
    transfer = manifest.create("c", "p", "c/p/image.jpg", 3, sha256(b"rgb").hexdigest())
    with pytest.raises(PermissionError):
        StagedTransferVerifier(manifest, Remote(b"rgb")).inspect(transfer, "other", "p")
