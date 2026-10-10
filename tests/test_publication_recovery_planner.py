from hashlib import sha256

from mcm_solarcheck.infrastructure.sqlite_publication_journal import SQLitePublicationJournal
from mcm_solarcheck.services.local_publication_reconciler import LocalPublicationReconciler
from mcm_solarcheck.services.publication_recovery_planner import PublicationRecoveryPlanner


def test_recovery_plan_tracks_missing_and_verified_final(tmp_path):
    journal = SQLitePublicationJournal(tmp_path / "journal.db")
    target = tmp_path / "final.bin"
    journal.prepare("t", "c", "p", str(target), 3, sha256(b"abc").hexdigest())
    assert journal.transition("t", "c", "p", "prepared", "publishing")
    planner = PublicationRecoveryPlanner(journal, LocalPublicationReconciler(journal))
    assert planner.plan("t", "c", "p").decision == "manual_retry_assessment"
    target.write_bytes(b"abc")
    plan = planner.plan("t", "c", "p")
    assert (plan.decision, plan.observed) == ("eligible_for_manual_state_reconciliation", "verified_final")
    assert journal.get("t", "c", "p")["state"] == "publishing"


def test_unknown_owner_has_no_recovery_plan(tmp_path):
    journal = SQLitePublicationJournal(tmp_path / "journal.db")
    planner = PublicationRecoveryPlanner(journal, LocalPublicationReconciler(journal))
    assert planner.plan("unknown", "c", "p").decision == "unknown_transfer"
