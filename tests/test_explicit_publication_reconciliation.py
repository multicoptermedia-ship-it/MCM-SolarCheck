from hashlib import sha256

from mcm_solarcheck.infrastructure.sqlite_publication_destinations import SQLitePublicationDestinations
from mcm_solarcheck.infrastructure.sqlite_publication_journal import SQLitePublicationJournal
from mcm_solarcheck.services.canonical_publication_recovery_assessment import CanonicalPublicationRecoveryAssessment
from mcm_solarcheck.services.explicit_publication_reconciliation import ExplicitPublicationReconciliation


class Transfers:
    def get(self, *args):
        return {"state": "pending", "expected_size": 3, "expected_sha256": sha256(b"abc").hexdigest()}


class Reconciler:
    def __init__(self, status):
        self.status = status

    def inspect(self, *args):
        return self.status


def test_explicit_reconciliation_requires_verified_file(tmp_path):
    root = tmp_path / "storage"
    root.mkdir()
    db = tmp_path / "journal.db"
    journal = SQLitePublicationJournal(db)
    destinations = SQLitePublicationDestinations(db)
    final = str(root / "c" / "p" / "t.bin")
    journal.prepare("t", "c", "p", final, 3, sha256(b"abc").hexdigest())
    destinations.reserve(final, "t", "c", "p")
    journal.transition("t", "c", "p", "prepared", "publishing")
    journal.transition("t", "c", "p", "publishing", "needs_review")
    reconciler = Reconciler("invalid_final")
    assessment = CanonicalPublicationRecoveryAssessment(root, Transfers(), journal, destinations, reconciler)
    recovery = ExplicitPublicationReconciliation(assessment, journal)
    assert recovery.reconcile_verified("t", "c", "p") == "requires_manual_review"
    assert journal.get("t", "c", "p")["state"] == "needs_review"
    reconciler.status = "verified_final"
    assert recovery.reconcile_verified("t", "c", "p") == "journal_reconciled"
    assert journal.get("t", "c", "p")["state"] == "published"
    assert recovery.reconcile_verified("t", "c", "p") == "already_verified"
