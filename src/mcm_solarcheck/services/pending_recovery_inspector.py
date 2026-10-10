"""Read-only triage of an interrupted, owner-scoped recovery request."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PendingRecoveryReview:
    decision: str
    attempt_state: str | None
    journal_decision: str | None
    audit_decisions: tuple[str, ...]


class PendingRecoveryInspector:
    def __init__(self, attempts, transfers, assessment, audit):
        self.attempts = attempts
        self.transfers = transfers
        self.assessment = assessment
        self.audit = audit

    def inspect(self, request_id, transfer_id, customer_id, project_id, operator_id):
        if self.transfers.get(transfer_id, customer_id, project_id) is None:
            return PendingRecoveryReview("unknown_transfer", None, None, ())
        attempt = self.attempts.inspect(request_id, transfer_id, customer_id, project_id, operator_id)
        if attempt is None:
            return PendingRecoveryReview("unknown_request", None, None, ())
        state, outcome = attempt
        if state == "completed":
            return PendingRecoveryReview("already_completed", state, None, ())
        if state != "pending":
            return PendingRecoveryReview("manual_review", state, None, ())
        assessment = self.assessment.assess(transfer_id, customer_id, project_id)
        events = self.audit.list_for_transfer(transfer_id, customer_id, project_id)
        decisions = tuple(row[2] for row in events if row[1] == operator_id)
        # Legacy audit events have no request_id: never infer that an event
        # belongs to this request, even if its operator matches.
        return PendingRecoveryReview("manual_review_required", state, assessment.decision, decisions)
