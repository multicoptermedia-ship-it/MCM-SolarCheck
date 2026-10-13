"""Reserve a canonical local destination before coordinated publication.

This prototype requires the caller to supply a trusted, server-generated path.
"""
from __future__ import annotations

from pathlib import Path

from mcm_solarcheck.services.local_publication_coordinator import LocalPublicationCoordinator


class ReservedLocalPublication:
    def __init__(self, transfers, journal, destinations, publisher=None, reconciler=None):
        self.transfers = transfers
        self.destinations = destinations
        self.coordinator = LocalPublicationCoordinator(
            transfers, journal, publisher=publisher, reconciler=reconciler
        )

    def publish(self, transfer_id, customer_id, project_id, *, source, destination):
        record = self.transfers.get(transfer_id, customer_id, project_id)
        if record is None:
            raise PermissionError("transfer not found for owner")
        if record["state"] != "pending":
            raise ValueError("transfer not pending")
        final = str(Path(destination).absolute())
        if not Path(final).is_absolute():
            raise ValueError("invalid destination")
        self.destinations.reserve(final, transfer_id, customer_id, project_id)
        return self.coordinator.publish(
            transfer_id, customer_id, project_id, source=source, destination=final
        )
