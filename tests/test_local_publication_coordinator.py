from hashlib import sha256

from mcm_solarcheck.infrastructure.sqlite_publication_journal import SQLitePublicationJournal
from mcm_solarcheck.services.local_publication_coordinator import LocalPublicationCoordinator


class Transfers:
    def get(self, transfer_id, customer_id, project_id):
        if (transfer_id, customer_id, project_id) != ("t", "c", "p"):
            return None
        return {"state": "pending", "expected_size": 3, "expected_sha256": sha256(b"abc").hexdigest()}


def test_coordinator_publishes_and_records_after_readback(tmp_path):
    journal = SQLitePublicationJournal(tmp_path / "journal.db")
    source = tmp_path / ".assembly-123"
    source.write_bytes(b"abc")
    destination = tmp_path / "final.bin"
    coordinator = LocalPublicationCoordinator(Transfers(), journal)
    assert coordinator.publish("t", "c", "p", source=source, destination=destination) == "published"
    assert destination.read_bytes() == b"abc"
    assert journal.get("t", "c", "p")["state"] == "published"
    assert coordinator.publish("t", "c", "p", source=source, destination=destination) == "already_recorded"


def test_coordinator_denies_wrong_owner_before_journal_write(tmp_path):
    journal = SQLitePublicationJournal(tmp_path / "journal.db")
    coordinator = LocalPublicationCoordinator(Transfers(), journal)
    try:
        coordinator.publish("t", "other", "p", source=tmp_path / ".assembly-123",
                            destination=tmp_path / "final.bin")
    except PermissionError:
        pass
    else:
        raise AssertionError("wrong owner accepted")
    assert journal.get("t", "other", "p") is None
