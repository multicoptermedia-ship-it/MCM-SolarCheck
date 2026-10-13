"""Explicit persistence of transient preflight outcomes, without automatic retries."""
from __future__ import annotations

from mcm_solarcheck.services.sftp_preflight_retry_policy import advise_sftp_preflight_retry
from mcm_solarcheck.services.sftp_preflight_outcomes import SFTPPreflightOutcome


class SFTPPreflightRetryRecorder:
    def __init__(self, ledger):
        self.ledger = ledger

    def record(self, outcome: SFTPPreflightOutcome, *, now=None):
        advice = advise_sftp_preflight_retry(outcome)
        if advice.decision != "retry_with_backoff":
            return ("not_retryable", 0, None)
        return self.ledger.record_failure(
            outcome.job_id, outcome.customer_id, outcome.project_id,
            outcome.failure_category, now=now,
        )
