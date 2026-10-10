from hashlib import sha256

from mcm_solarcheck.infrastructure.sqlite_publication_journal import SQLitePublicationJournal
from mcm_solarcheck.services.local_publication_reconciler import LocalPublicationReconciler


def test_recovery_detects_verified_final_after_restart(tmp_path):
    journal = SQLitePublicationJournal(tmp_path / "journal.db")
    destination = tmp_path / "final.bin"
    payload = b"fully verified"
    journal.prepare("t", "c", "p", str(destination), len(payload), sha256(payload).hexdigest())
    assert journal.transition("t", "c", "p", "prepared", "publishing")
    restarted = LocalPublicationReconciler(SQLitePublicationJournal(tmp_path / "journal.db"), chunk_size=3)
    assert restarted.inspect("t", "c", "p") == "missing_final"
    destination.write_bytes(payload)
    assert restarted.inspect("t", "c", "p") == "verified_final"
    destination.write_bytes(b"corrupted")
    assert restarted.inspect("t", "c", "p") == "invalid_final"


def test_wrong_owner_and_untracked_transfer_are_not_inspected(tmp_path):
    journal = SQLitePublicationJournal(tmp_path / "journal.db")
    destination = tmp_path / "final.bin"
    journal.prepare("t", "c", "p", str(destination), 3, sha256(b"abc").hexdigest())
    assert LocalPublicationReconciler(journal).inspect("t", "other", "p") == "not_found"
    assert LocalPublicationReconciler(journal).inspect("unknown", "c", "p") == "not_found"
