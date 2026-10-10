"""Idempotent wrapper: ambiguous pending attempts require manual investigation.

No automatic replay of a request whose journal transition may already have run.
"""
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
        if state == "pending":
            # Distinguish newly claimed requests from preexisting pending
            # records via a separate explicit first-claim API, not by guessing.
            return "pending_requires_review"
        return "pending_requires_review"
