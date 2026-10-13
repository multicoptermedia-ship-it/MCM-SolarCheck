from hashlib import sha256

import pytest

from mcm_solarcheck.infrastructure.sqlite_publication_destinations import SQLitePublicationDestinations
from mcm_solarcheck.infrastructure.sqlite_publication_journal import SQLitePublicationJournal
from mcm_solarcheck.services.reserved_local_publication import ReservedLocalPublication


class Transfers:
    def get(self, transfer_id, customer_id, project_id):
        if customer_id not in ("c1", "c2"):
            return None
        return {"state": "pending", "expected_size": 3, "expected_sha256": sha256(b"abc").hexdigest()}


def test_competing_customers_cannot_reserve_same_final_path(tmp_path):
    database = tmp_path / "journal.db"
    service = ReservedLocalPublication(
        Transfers(), SQLitePublicationJournal(database), SQLitePublicationDestinations(database)
    )
    source = tmp_path / ".assembly-abc"
    source.write_bytes(b"abc")
    final = tmp_path / "final.bin"
    assert service.publish("t1", "c1", "p", source=source, destination=final) == "published"
    with pytest.raises(ValueError):
        service.publish("t2", "c2", "p", source=source, destination=final)
    assert final.read_bytes() == b"abc"


def test_wrong_owner_cannot_create_reservation(tmp_path):
    database = tmp_path / "journal.db"
    destinations = SQLitePublicationDestinations(database)
    service = ReservedLocalPublication(Transfers(), SQLitePublicationJournal(database), destinations)
    with pytest.raises(PermissionError):
        service.publish("t", "other", "p", source=tmp_path / ".assembly-a",
                        destination=tmp_path / "final.bin")
    assert destinations.lookup(str((tmp_path / "final.bin").absolute())) is None
