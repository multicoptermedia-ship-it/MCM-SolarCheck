from hashlib import sha256

from mcm_solarcheck.infrastructure.sqlite_publication_destinations import SQLitePublicationDestinations
from mcm_solarcheck.infrastructure.sqlite_publication_journal import SQLitePublicationJournal
from mcm_solarcheck.services.reserved_local_publication import ReservedLocalPublication


class Transfers:
    def get(self, transfer_id, customer_id, project_id):
        if customer_id != "c" or project_id != "p" or transfer_id not in ("t1", "t2"):
            return None
        return {"state": "pending", "expected_size": 3, "expected_sha256": sha256(b"abc").hexdigest()}


def test_reserved_publication_creates_final_and_persistent_reservation(tmp_path):
    database = tmp_path / "journal.db"
    journal = SQLitePublicationJournal(database)
    destinations = SQLitePublicationDestinations(database)
    source = tmp_path / ".assembly-abc"
    source.write_bytes(b"abc")
    final = tmp_path / "final.bin"
    service = ReservedLocalPublication(Transfers(), journal, destinations)
    assert service.publish("t1", "c", "p", source=source, destination=final) == "published"
    assert final.read_bytes() == b"abc"
    assert SQLitePublicationDestinations(database).lookup(str(final.absolute())) == ("t1", "c", "p")
    assert service.publish("t1", "c", "p", source=source, destination=final) == "already_recorded"
