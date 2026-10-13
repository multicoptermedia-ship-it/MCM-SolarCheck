from hashlib import sha256

import pytest

from mcm_solarcheck.infrastructure.sqlite_publication_destinations import SQLitePublicationDestinations
from mcm_solarcheck.infrastructure.sqlite_publication_journal import SQLitePublicationJournal
from mcm_solarcheck.infrastructure.sqlite_recovery_audit import SQLiteRecoveryAudit
from mcm_solarcheck.services.audited_publication_recovery import AuditedPublicationRecovery
from mcm_solarcheck.services.canonical_publication_recovery_assessment import CanonicalPublicationRecoveryAssessment
from mcm_solarcheck.services.explicit_publication_reconciliation import ExplicitPublicationReconciliation


class Transfers:
    def get(self, *args):
        return {"state": "pending", "expected_size": 3, "expected_sha256": sha256(b"abc").hexdigest()}


class Verifier:
    def __init__(self, result):
        self.result = result

    def inspect(self, *args):
        return self.result


def setup(tmp_path, result):
    root = tmp_path / "storage"
    root.mkdir()
    db = tmp_path / "publication.db"
    journal = SQLitePublicationJournal(db)
    reservations = SQLitePublicationDestinations(db)
    audit = SQLiteRecoveryAudit(db)
    final = str(root / "c" / "p" / "t.bin")
    journal.prepare("t", "c", "p", final, 3, sha256(b"abc").hexdigest())
    reservations.reserve(final, "t", "c", "p")
    journal.transition("t", "c", "p", "prepared", "publishing")
    journal.transition("t", "c", "p", "publishing", "needs_review")
    assessment = CanonicalPublicationRecoveryAssessment(root, Transfers(), journal, reservations, Verifier(result))
    recovery = AuditedPublicationRecovery(ExplicitPublicationReconciliation(assessment, journal), audit)
    return recovery, audit, journal


def test_success_records_intent_and_outcome(tmp_path):
    recovery, audit, journal = setup(tmp_path, "verified_final")
    assert recovery.reconcile_verified("t", "c", "p", operator_id="operator-1") == "journal_reconciled"
    assert [row[2] for row in audit.list_for_transfer("t", "c", "p")] == ["requested", "journal_reconciled"]
    assert journal.get("t", "c", "p")["state"] == "published"


def test_rejection_is_audited(tmp_path):
    recovery, audit, journal = setup(tmp_path, "invalid_final")
    assert recovery.reconcile_verified("t", "c", "p", operator_id="operator-1") == "requires_manual_review"
    assert [row[2] for row in audit.list_for_transfer("t", "c", "p")] == ["requested", "requires_manual_review"]
    assert journal.get("t", "c", "p")["state"] == "needs_review"


def test_missing_operator_rejected_without_changes(tmp_path):
    recovery, audit, journal = setup(tmp_path, "verified_final")
    with pytest.raises(ValueError):
        recovery.reconcile_verified("t", "c", "p", operator_id="")
    assert audit.list_for_transfer("t", "c", "p") == []
    assert journal.get("t", "c", "p")["state"] == "needs_review"
