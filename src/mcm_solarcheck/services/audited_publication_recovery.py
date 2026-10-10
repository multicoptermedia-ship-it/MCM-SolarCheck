"""Explicit operator-only recovery with fail-closed audit ordering.

Authentication/authorization must be performed by a trusted caller. This
wrapper does not expose an HTTP endpoint or schedule automatic recovery.
"""
from __future__ import annotations


class AuditedPublicationRecovery:
    def __init__(self, recovery, audit):
        self.recovery = recovery
        self.audit = audit

    def reconcile_verified(self, transfer_id, customer_id, project_id, *, operator_id):
        if not isinstance(operator_id, str) or not 0 < len(operator_id) <= 256:
            raise ValueError("authenticated operator identity required")
        # A failed durable intent write must prevent any journal transition.
        self.audit.record(transfer_id, customer_id, project_id, operator_id, "requested")
        try:
            result = self.recovery.reconcile_verified(transfer_id, customer_id, project_id)
        except Exception:
            # Do not mask the original failure if the outcome audit also fails.
            try:
                self.audit.record(transfer_id, customer_id, project_id, operator_id, "raised_exception")
            except Exception:
                pass
            raise
        # A result-audit failure is propagated, never silently treated as success.
        # The journal may already have changed: callers must reconcile on retry.
        self.audit.record(transfer_id, customer_id, project_id, operator_id, result)
        return result
