from hashlib import sha256

from mcm_solarcheck.infrastructure.sqlite_publication_destinations import SQLitePublicationDestinations
from mcm_solarcheck.infrastructure.sqlite_publication_journal import SQLitePublicationJournal
from mcm_solarcheck.services.canonical_reserved_local_publication import CanonicalReservedLocalPublication


class Transfers:
    def get(self, transfer_id, customer_id, project_id):
        if (transfer_id, customer_id, project_id) != ("t1", "c1", "p1"):
            return None
        return {"state": "pending", "expected_size": 3, "expected_sha256": sha256(b"abc").hexdigest()}


def test_canonical_publication_uses_server_derived_path(tmp_path):
    root = tmp_path / "storage"
    (root / "c1" / "p1").mkdir(parents=True)
    db = tmp_path / "journal.db"
    service = CanonicalReservedLocalPublication(
        root, Transfers(), SQLitePublicationJournal(db), SQLitePublicationDestinations(db)
    )
    source = tmp_path / ".assembly-private"
    source.write_bytes(b"abc")
    assert service.publish("t1", "c1", "p1", source=source) == "published"
    final = root / "c1" / "p1" / "t1.bin"
    assert final.read_bytes() == b"abc"
    assert service.destination_for("t1", "c1", "p1") == final
