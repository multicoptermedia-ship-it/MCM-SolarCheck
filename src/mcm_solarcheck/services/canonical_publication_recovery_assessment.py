"""Read-only, fail-closed decisions for interrupted canonical publications."""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.canonical_local_destination import canonical_local_destination


@dataclass(frozen=True)
class CanonicalRecoveryAssessment:
    decision: str
    journal_state: str | None
    observed: str
    reservation: str


class CanonicalPublicationRecoveryAssessment:
    def __init__(self, root, transfers, journal, destinations, reconciler):
        self.root = root
        self.transfers = transfers
        self.journal = journal
        self.destinations = destinations
        self.reconciler = reconciler

    def assess(self, transfer_id, customer_id, project_id):
        transfer = self.transfers.get(transfer_id, customer_id, project_id)
        if transfer is None:
            return CanonicalRecoveryAssessment("unknown_transfer", None, "not_checked", "not_checked")
        record = self.journal.get(transfer_id, customer_id, project_id)
        if record is None:
            return CanonicalRecoveryAssessment("no_journal", None, "not_checked", "not_checked")
        expected = str(canonical_local_destination(self.root, customer_id, project_id, transfer_id))
        if record["destination"] != expected or (
            record["expected_size"] != transfer["expected_size"]
            or record["expected_sha256"] != transfer["expected_sha256"]
        ):
            return CanonicalRecoveryAssessment("identity_mismatch", record["state"], "not_checked", "not_checked")
        reservation = self.destinations.lookup(expected)
        if reservation != (transfer_id, customer_id, project_id):
            return CanonicalRecoveryAssessment("reservation_mismatch", record["state"], "not_checked", "missing_or_conflicting")
        observed = self.reconciler.inspect(transfer_id, customer_id, project_id)
        if observed == "verified_final":
            if record["state"] == "published":
                return CanonicalRecoveryAssessment("verified_complete", record["state"], observed, "matching")
            if record["state"] == "needs_review":
                return CanonicalRecoveryAssessment("eligible_for_explicit_reconciliation", record["state"], observed, "matching")
            return CanonicalRecoveryAssessment("manual_state_review", record["state"], observed, "matching")
        if observed == "missing_final":
            return CanonicalRecoveryAssessment("manual_missing_file_review", record["state"], observed, "matching")
        return CanonicalRecoveryAssessment("manual_integrity_review", record["state"], observed, "matching")
