"""Read-only operator audit inspection, scoped to a single transfer owner."""
from __future__ import annotations


class RecoveryAuditInspection:
    def __init__(self, transfers, audit):
        self.transfers = transfers
        self.audit = audit

    def list_events(self, transfer_id, customer_id, project_id):
        if self.transfers.get(transfer_id, customer_id, project_id) is None:
            return None
        return self.audit.list_for_transfer(transfer_id, customer_id, project_id)
