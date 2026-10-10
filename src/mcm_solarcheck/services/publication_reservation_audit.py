"""Read-only checks for inconsistent reservation and publication journal state."""
from __future__ import annotations


class PublicationReservationAudit:
    def __init__(self, journal, destinations):
        self.journal = journal
        self.destinations = destinations

    def inspect(self, transfer_id, customer_id, project_id):
        record = self.journal.get(transfer_id, customer_id, project_id)
        if record is None:
            return "no_journal_record"
        owner = self.destinations.lookup(record["destination"])
        if owner is None:
            return "missing_reservation"
        if owner != (transfer_id, customer_id, project_id):
            return "conflicting_reservation"
        return "consistent_metadata"
