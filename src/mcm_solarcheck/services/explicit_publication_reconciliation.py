"""Explicit, conservative journal-only reconciliation of verified local publications."""
from __future__ import annotations


class ExplicitPublicationReconciliation:
    def __init__(self, assessment, journal):
        self.assessment = assessment
        self.journal = journal

    def reconcile_verified(self, transfer_id, customer_id, project_id):
        assessment = self.assessment.assess(transfer_id, customer_id, project_id)
        if assessment.decision == "verified_complete":
            return "already_verified"
        if assessment.decision != "eligible_for_explicit_reconciliation":
            return "requires_manual_review"
        # No filesystem write and no automatic retries. Compare-and-swap
        # refuses unexpected concurrent journal transitions.
        if not self.journal.transition(
            transfer_id, customer_id, project_id, "needs_review", "published"
        ):
            return "state_changed_review_required"
        return "journal_reconciled"
