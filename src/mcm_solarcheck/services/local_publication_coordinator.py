"""Conservative local publication coordinator; no automatic retry of ambiguous writes."""
from __future__ import annotations

from pathlib import Path

from mcm_solarcheck.infrastructure.exclusive_local_publisher import ExclusiveLocalPublisher
from mcm_solarcheck.services.local_publication_reconciler import LocalPublicationReconciler


class LocalPublicationCoordinator:
    def __init__(self, transfers, journal, publisher=None, reconciler=None):
        self.transfers = transfers
        self.journal = journal
        self.publisher = publisher or ExclusiveLocalPublisher()
        self.reconciler = reconciler or LocalPublicationReconciler(journal)

    def publish(self, transfer_id, customer_id, project_id, *, source, destination):
        transfer = self.transfers.get(transfer_id, customer_id, project_id)
        if transfer is None:
            raise PermissionError("transfer not found for owner")
        if transfer["state"] != "pending":
            raise ValueError("transfer not pending")
        destination = str(Path(destination).absolute())
        record = self.journal.prepare(
            transfer_id, customer_id, project_id, destination,
            transfer["expected_size"], transfer["expected_sha256"]
        )
        if record["state"] == "published":
            return "already_recorded"
        if record["state"] != "prepared":
            return "needs_reconciliation"
        if not self.journal.transition(transfer_id, customer_id, project_id, "prepared", "publishing"):
            return "needs_reconciliation"
        try:
            self.publisher.publish(
                source, destination, expected_size=record["expected_size"],
                expected_sha256=record["expected_sha256"]
            )
        except BaseException:
            # An exclusive link may have succeeded before fsync or the caller crashed.
            # Never retry publication without an explicit reconciliation.
            self.journal.transition(transfer_id, customer_id, project_id, "publishing", "needs_review")
            raise
        status = self.reconciler.inspect(transfer_id, customer_id, project_id)
        if status != "verified_final":
            self.journal.transition(transfer_id, customer_id, project_id, "publishing", "needs_review")
            return "needs_review"
        if not self.journal.transition(transfer_id, customer_id, project_id, "publishing", "published"):
            return "needs_reconciliation"
        return "published"
