from hashlib import sha256
from io import BytesIO

import pytest

from mcm_solarcheck.infrastructure.sqlite_transfer_manifest import SQLiteTransferManifest
from mcm_solarcheck.services.staged_resume_inspector import StagedResumeInspector


class Remote:
    def __init__(self, content):
        self.content = content

    def read_staging_chunks(self, key, chunk_size):
        for start in range(0, len(self.content), chunk_size):
            yield self.content[start:start + chunk_size]


def make_manifest(tmp_path):
    manifest = SQLiteTransferManifest(tmp_path / "db.sqlite")
    transfer = manifest.create("customer", "project", "customer/project/image.jpg", 6, sha256(b"abcdef").hexdigest())
    return manifest, transfer


def test_matching_prefix_reports_verified_offset(tmp_path):
    manifest, transfer = make_manifest(tmp_path)
    result = StagedResumeInspector(manifest, Remote(b"abc"), chunk_size=2).inspect(
        transfer, "customer", "project", BytesIO(b"abcdef")
    )
    assert (result.status, result.verified_offset) == ("verified_prefix", 3)
    assert manifest.get(transfer, "customer", "project")["state"] == "pending"


@pytest.mark.parametrize("remote,status", [
    (b"abX", "prefix_mismatch"),
    (b"abcdefg", "size_mismatch"),
    (b"abcdef", "complete_prefix"),
])
def test_prefix_inspection_outcomes(tmp_path, remote, status):
    manifest, transfer = make_manifest(tmp_path)
    result = StagedResumeInspector(manifest, Remote(remote), chunk_size=2).inspect(
        transfer, "customer", "project", BytesIO(b"abcdef")
    )
    assert result.status == status


def test_cross_customer_resume_inspection_is_forbidden(tmp_path):
    manifest, transfer = make_manifest(tmp_path)
    with pytest.raises(PermissionError):
        StagedResumeInspector(manifest, Remote(b"abc")).inspect(
            transfer, "another", "project", BytesIO(b"abcdef")
        )
