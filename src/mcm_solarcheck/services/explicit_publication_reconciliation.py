"""Explicit journal reconciliation with local serialization and repeated checks.

No distributed fencing: a writer may still change file bytes after verification.
"""
from __future__ import annotations

from mcm_solarcheck.services.process_local_recovery_locks import ProcessLocalRecoveryLocks


class ExplicitPublicationReconciliation:
    def __init__(self, assessment, journal, *, locks=None):
        self.assessment = assessment
        self.journal = journal
        self.locks = locks or ProcessLocalRecoveryLocks()

    def reconcile_verified(self, transfer_id, customer_id, project_id):
        acquired, lock = self.locks.acquire(transfer_id, customer_id, project_id)
        if not acquired:
            return "recovery_in_progress"
        try:
            first = self.assessment.assess(transfer_id, customer_id, project_id)
            if first.decision == "verified_complete":
                return "already_verified"
            if first.decision != "eligible_for_explicit_reconciliation":
                return "requires_manual_review"
            # Repeat all owner/reservation/hash checks immediately before CAS.
            # This narrows but cannot eliminate the filesystem-to-SQLite race.
            second = self.assessment.assess(transfer_id, customer_id, project_id)
            if second != first:
                return "assessment_changed_review_required"
            if not self.journal.transition(
                transfer_id, customer_id, project_id, "needs_review", "published"
            ):
                return "state_changed_review_required"
            return "journal_reconciled"
        finally:
            self.locks.release(lock)
