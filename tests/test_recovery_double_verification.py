from hashlib import sha256

from mcm_solarcheck.infrastructure.sqlite_publication_destinations import SQLitePublicationDestinations
from mcm_solarcheck.infrastructure.sqlite_publication_journal import SQLitePublicationJournal
from mcm_solarcheck.services.canonical_publication_recovery_assessment import CanonicalPublicationRecoveryAssessment
from mcm_solarcheck.services.explicit_publication_reconciliation import ExplicitPublicationReconciliation
from mcm_solarcheck.services.process_local_recovery_locks import ProcessLocalRecoveryLocks


class Transfers:
    def get(self, *args):
        return {"state": "pending", "expected_size": 3, "expected_sha256": sha256(b"abc").hexdigest()}


class FlippingReconciler:
    def __init__(self):
        self.calls = 0

    def inspect(self, *args):
        self.calls += 1
        return "verified_final" if self.calls == 1 else "invalid_final"


def test_second_verification_blocks_changed_file(tmp_path):
    root = tmp_path / "storage"
    root.mkdir()
    db = tmp_path / "journal.db"
    journal = SQLitePublicationJournal(db)
    reservations = SQLitePublicationDestinations(db)
    final = str(root / "c" / "p" / "t.bin")
    journal.prepare("t", "c", "p", final, 3, sha256(b"abc").hexdigest())
    reservations.reserve(final, "t", "c", "p")
    journal.transition("t", "c", "p", "prepared", "publishing")
    journal.transition("t", "c", "p", "publishing", "needs_review")
    verifier = FlippingReconciler()
    assessment = CanonicalPublicationRecoveryAssessment(root, Transfers(), journal, reservations, verifier)
    recovery = ExplicitPublicationReconciliation(assessment, journal)
    assert recovery.reconcile_verified("t", "c", "p") == "assessment_changed_review_required"
    assert verifier.calls == 2
    assert journal.get("t", "c", "p")["state"] == "needs_review"


def test_process_local_lock_refuses_concurrent_attempt():
    locks = ProcessLocalRecoveryLocks()
    acquired, lock = locks.acquire("t", "c", "p")
    assert acquired
    try:
        acquired_again, _ = locks.acquire("t", "c", "p")
        assert not acquired_again
    finally:
        locks.release(lock)
    acquired_after, lock_after = locks.acquire("t", "c", "p")
    assert acquired_after
    locks.release(lock_after)
