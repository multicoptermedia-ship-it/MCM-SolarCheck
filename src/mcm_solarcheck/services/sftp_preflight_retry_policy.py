"""Conservative retry eligibility for isolated SFTP preflight failures.

This is advisory only: no sleeps, network retries, timers or job mutations.
"""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.sftp_preflight_outcomes import SFTPPreflightOutcome


@dataclass(frozen=True)
class SFTPPreflightRetryAdvice:
    decision: str
    max_attempts: int


def advise_sftp_preflight_retry(outcome: SFTPPreflightOutcome) -> SFTPPreflightRetryAdvice:
    if not isinstance(outcome, SFTPPreflightOutcome):
        raise TypeError("SFTPPreflightOutcome required")
    if outcome.status == "ready":
        return SFTPPreflightRetryAdvice("no_retry_needed", 0)
    if outcome.status == "failed" and outcome.failure_category in ("timeout", "network"):
        return SFTPPreflightRetryAdvice("retry_with_backoff", 3)
    return SFTPPreflightRetryAdvice("manual_review", 0)
