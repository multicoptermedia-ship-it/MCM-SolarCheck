"""Transfer-owner-scoped local publication with canonical expected integrity."""
from __future__ import annotations

from mcm_solarcheck.infrastructure.exclusive_local_publisher import ExclusiveLocalPublisher


class AuthorizedLocalPublication:
    def __init__(self, transfers, publisher=None):
        self.transfers = transfers
        self.publisher = publisher or ExclusiveLocalPublisher()

    def publish(self, transfer_id: str, customer_id: str, project_id: str,
                *, source, destination):
        transfer = self.transfers.get(transfer_id, customer_id, project_id)
        if transfer is None:
            raise PermissionError("transfer not found for owner")
        if transfer["state"] != "pending":
            raise ValueError("transfer not pending")
        # This wrapper intentionally does not transition transfer state.
        # Production requires a durable exclusive publication claim and reconciliation.
        return self.publisher.publish(
            source, destination,
            expected_size=transfer["expected_size"],
            expected_sha256=transfer["expected_sha256"],
        )
