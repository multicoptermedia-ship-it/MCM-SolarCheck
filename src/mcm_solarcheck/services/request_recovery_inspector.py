"""Read-only triage with request-correlated audit events."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RequestRecoveryReview:
    decision: str
    attempt_state: str | None
    assessment_decision: str | None
    recorded_outcome: str | None
    audit_decisions: tuple[str, ...]


class RequestRecoveryInspector:
    def __init__(self, attempts, transfers, assessment, request_audit):
        self.attempts = attempts
        self.transfers = transfers
        self.assessment = assessment
        self.request_audit = request_audit

    def inspect(self, request_id, transfer_id, customer_id, project_id, operator_id):
        if self.transfers.get(transfer_id, customer_id, project_id) is None:
            return RequestRecoveryReview("unknown_transfer", None, None, None, ())
        attempt = self.attempts.inspect(request_id, transfer_id, customer_id, project_id, operator_id)
        if attempt is None:
            return RequestRecoveryReview("unknown_request", None, None, None, ())
        state, outcome = attempt
        events = self.request_audit.list_for_request(request_id, transfer_id, customer_id, project_id, operator_id)
        decisions = tuple(row[1] for row in events)
        if state == "completed":
            return RequestRecoveryReview("recorded_complete", state, None, outcome, decisions)
        if state != "pending":
            return RequestRecoveryReview("manual_review_required", state, None, outcome, decisions)
        assessment = self.assessment.assess(transfer_id, customer_id, project_id)
        return RequestRecoveryReview("manual_review_required", state, assessment.decision, outcome, decisions)
