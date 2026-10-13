from hashlib import sha256

import pytest

from mcm_solarcheck.infrastructure.sqlite_publication_journal import SQLitePublicationJournal
from mcm_solarcheck.services.local_publication_coordinator import LocalPublicationCoordinator


class Transfers:
    def get(self, *args):
        return {"state": "pending", "expected_size": 3, "expected_sha256": sha256(b"abc").hexdigest()}


def test_existing_final_file_never_overwritten_and_attempt_needs_review(tmp_path):
    journal = SQLitePublicationJournal(tmp_path / "journal.db")
    source = tmp_path / ".assembly-123"
    source.write_bytes(b"abc")
    final = tmp_path / "final.bin"
    final.write_bytes(b"original")
    coordinator = LocalPublicationCoordinator(Transfers(), journal)
    with pytest.raises(FileExistsError):
        coordinator.publish("t", "c", "p", source=source, destination=final)
    assert final.read_bytes() == b"original"
    assert journal.get("t", "c", "p")["state"] == "needs_review"
    assert coordinator.publish("t", "c", "p", source=source, destination=final) == "needs_reconciliation"


def test_corrupt_source_cannot_publish_or_mark_success(tmp_path):
    journal = SQLitePublicationJournal(tmp_path / "journal.db")
    source = tmp_path / ".assembly-123"
    source.write_bytes(b"bad")
    final = tmp_path / "final.bin"
    with pytest.raises(ValueError):
        LocalPublicationCoordinator(Transfers(), journal).publish(
            "t", "c", "p", source=source, destination=final
        )
    assert not final.exists()
    assert journal.get("t", "c", "p")["state"] == "needs_review"
