"""Read-only decision support for publication attempts left in an ambiguous state."""
from __future__ import annotations


class PublicationRecoveryAdvisor:
    def __init__(self, journal, reconciler):
        self.journal = journal
        self.reconciler = reconciler

    def inspect(self, transfer_id, customer_id, project_id):
        record = self.journal.get(transfer_id, customer_id, project_id)
        if record is None:
            return "unknown_transfer"
        if record["state"] == "published":
            return "recorded_complete_unchecked"
        observed = self.reconciler.inspect(transfer_id, customer_id, project_id)
        if observed == "verified_final":
            return "verified_final_requires_state_reconciliation"
        if observed == "missing_final":
            return "missing_final_requires_operator_review"
        if observed in ("invalid_final", "changed_during_read"):
            return "unsafe_final_requires_operator_review"
        return "unavailable_requires_operator_review"
