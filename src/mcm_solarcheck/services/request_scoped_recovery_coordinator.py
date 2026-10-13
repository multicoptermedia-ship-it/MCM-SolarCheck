"""Idempotent request-audited recovery with no automatic replay of pending work."""
from __future__ import annotations


class RequestScopedRecoveryCoordinator:
    def __init__(self, recovery, attempts):
        self.recovery = recovery
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
            return "pending_requires_review"
        result = self.recovery.reconcile_verified(
            transfer_id, customer_id, project_id,
            operator_id=operator_id, request_id=request_id
        )
        if not self.attempts.complete(
            request_id, transfer_id, customer_id, project_id, operator_id, result
        ):
            return "completion_requires_review"
        return result
