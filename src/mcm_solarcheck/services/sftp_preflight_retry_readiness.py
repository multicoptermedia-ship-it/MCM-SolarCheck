"""Read-only retry eligibility assessment; never initiates a network request."""
from __future__ import annotations

from datetime import datetime, timezone


class SFTPPreflightRetryReadiness:
    def __init__(self, ledger):
        self.ledger = ledger

    def assess(self, job_id, customer_id, project_id, *, now=None):
        record = self.ledger.inspect(job_id, customer_id, project_id)
        if record is None:
            return "unrecorded"
        if record["state"] == "exhausted":
            return "manual_review"
        if record["state"] != "waiting" or record["attempts"] >= 3:
            return "manual_review"
        instant = now if now is not None else datetime.now(timezone.utc)
        if not isinstance(instant, datetime) or instant.tzinfo is None:
            raise ValueError("timezone-aware now required")
        deadline = datetime.fromisoformat(record["next_attempt_at"])
        if deadline.tzinfo is None:
            return "manual_review"
        return "eligible" if instant >= deadline else "wait"
