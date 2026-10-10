import os
from hashlib import sha256

import pytest

from mcm_solarcheck.infrastructure.sqlite_publication_destinations import SQLitePublicationDestinations
from mcm_solarcheck.infrastructure.sqlite_publication_journal import SQLitePublicationJournal
from mcm_solarcheck.services.canonical_reserved_local_publication import CanonicalReservedLocalPublication


class Transfers:
    def get(self, transfer_id, customer_id, project_id):
        if (transfer_id, customer_id, project_id) != ("transfer", "customer", "project"):
            return None
        return {"state": "pending", "expected_size": 3, "expected_sha256": sha256(b"abc").hexdigest()}


@pytest.mark.skipif(os.name != "posix", reason="POSIX required")
def test_canonical_reserved_workflow_uses_descriptor_publisher(tmp_path):
    root = tmp_path / "storage"
    project = root / "customer" / "project"
    project.mkdir(parents=True)
    database = tmp_path / "journal.db"
    service = CanonicalReservedLocalPublication(
        root, Transfers(), SQLitePublicationJournal(database),
        SQLitePublicationDestinations(database)
    )
    source = tmp_path / ".assembly-123"
    source.write_bytes(b"abc")
    assert service.publish("transfer", "customer", "project", source=source) == "published"
    assert (project / "transfer.bin").read_bytes() == b"abc"
    assert service.publish("transfer", "customer", "project", source=source) == "already_recorded"


@pytest.mark.skipif(os.name != "posix", reason="POSIX required")
def test_canonical_reserved_workflow_rejects_wrong_owner(tmp_path):
    root = tmp_path / "storage"
    (root / "other" / "project").mkdir(parents=True)
    database = tmp_path / "journal.db"
    service = CanonicalReservedLocalPublication(
        root, Transfers(), SQLitePublicationJournal(database),
        SQLitePublicationDestinations(database)
    )
    source = tmp_path / ".assembly-123"
    source.write_bytes(b"abc")
    with pytest.raises(PermissionError):
        service.publish("transfer", "other", "project", source=source)
    assert not (root / "other" / "project" / "transfer.bin").exists()
