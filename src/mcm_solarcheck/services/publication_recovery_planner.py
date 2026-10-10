"""Conservative, read-only recovery planning for interrupted local publication."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PublicationRecoveryPlan:
    decision: str
    journal_state: str | None
    observed: str


class PublicationRecoveryPlanner:
    def __init__(self, journal, reconciler):
        self.journal = journal
        self.reconciler = reconciler

    def plan(self, transfer_id, customer_id, project_id):
        record = self.journal.get(transfer_id, customer_id, project_id)
        if record is None:
            return PublicationRecoveryPlan("unknown_transfer", None, "not_checked")
        # Never equate a recorded state with a fresh integrity check.
        observed = self.reconciler.inspect(transfer_id, customer_id, project_id)
        state = record["state"]
        if state == "published":
            return PublicationRecoveryPlan("recorded_complete_requires_fresh_verification", state, observed)
        if observed == "verified_final":
            return PublicationRecoveryPlan("eligible_for_manual_state_reconciliation", state, observed)
        if observed == "missing_final":
            return PublicationRecoveryPlan("manual_retry_assessment", state, observed)
        return PublicationRecoveryPlan("manual_integrity_investigation", state, observed)
