from hashlib import sha256

from mcm_solarcheck.infrastructure.sqlite_publication_destinations import SQLitePublicationDestinations
from mcm_solarcheck.infrastructure.sqlite_publication_journal import SQLitePublicationJournal
from mcm_solarcheck.services.canonical_publication_recovery_assessment import CanonicalPublicationRecoveryAssessment


class Transfers:
    def get(self, transfer_id, customer_id, project_id):
        if (transfer_id, customer_id, project_id) != ("t", "c", "p"):
            return None
        return {"state": "pending", "expected_size": 3, "expected_sha256": sha256(b"abc").hexdigest()}


class Reconciler:
    def __init__(self, status):
        self.status = status

    def inspect(self, *args):
        return self.status


def make(tmp_path, status):
    root = tmp_path / "storage"
    root.mkdir()
    db = tmp_path / "records.db"
    journal = SQLitePublicationJournal(db)
    destinations = SQLitePublicationDestinations(db)
    final = str(root / "c" / "p" / "t.bin")
    journal.prepare("t", "c", "p", final, 3, sha256(b"abc").hexdigest())
    destinations.reserve(final, "t", "c", "p")
    assert journal.transition("t", "c", "p", "prepared", "publishing")
    assert journal.transition("t", "c", "p", "publishing", "needs_review")
    return CanonicalPublicationRecoveryAssessment(root, Transfers(), journal, destinations, Reconciler(status)), journal


def test_verified_needs_review_is_eligible(tmp_path):
    assessment, _ = make(tmp_path, "verified_final")
    result = assessment.assess("t", "c", "p")
    assert result.decision == "eligible_for_explicit_reconciliation"


def test_invalid_or_missing_file_never_eligible(tmp_path):
    for status in ("invalid_final", "missing_final", "changed_during_read", "unavailable"):
        case = tmp_path / status
        case.mkdir()
        assessment, _ = make(case, status)
        assert assessment.assess("t", "c", "p").decision != "eligible_for_explicit_reconciliation"


def test_wrong_owner_is_not_exposed(tmp_path):
    assessment, _ = make(tmp_path, "verified_final")
    assert assessment.assess("t", "other", "p").decision == "unknown_transfer"
