"""Execute a newly claimed recovery with request-correlated audit events.

Trusted caller must authenticate/authorize operator_id before invoking this service.
"""
from __future__ import annotations


class RequestAuditedRecovery:
    def __init__(self, recovery, request_audit):
        self.recovery = recovery
        self.request_audit = request_audit

    def reconcile_verified(self, transfer_id, customer_id, project_id, *, operator_id, request_id):
        fields = (request_id, transfer_id, customer_id, project_id, operator_id)
        if not all(isinstance(value, str) and 0 < len(value) <= 256 for value in fields):
            raise ValueError("valid request and authenticated operator identities required")
        self.request_audit.record(*fields, "requested")
        try:
            result = self.recovery.reconcile_verified(transfer_id, customer_id, project_id)
        except Exception:
            try:
                self.request_audit.record(*fields, "raised_exception")
            except Exception:
                pass
            raise
        self.request_audit.record(*fields, result)
        return result
