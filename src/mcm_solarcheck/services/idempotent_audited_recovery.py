"""Idempotent audited recovery with fail-closed ambiguous crash handling."""
from __future__ import annotations


class IdempotentAuditedRecovery:
    def __init__(self, audited_recovery, attempts):
        self.audited_recovery = audited_recovery
        self.attempts = attempts

    def reconcile_verified(self, transfer_id, customer_id, project_id, *, operator_id, request_id):
        state, outcome = self.attempts.claim(
            request_id, transfer_id, customer_id, project_id, operator_id
        )
        if state == "identity_conflict":
            return "request_identity_conflict"
        if state == "completed":
            return outcome
        if state != "new":
            # Existing pending request may have changed the journal already.
            return "pending_requires_review"
        # Failure leaves pending: never blindly replay a potentially applied CAS.
        result = self.audited_recovery.reconcile_verified(
            transfer_id, customer_id, project_id, operator_id=operator_id
        )
        if not self.attempts.complete(
            request_id, transfer_id, customer_id, project_id, operator_id, result
        ):
            return "completion_requires_review"
        return result
