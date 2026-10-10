"""Read-only review of legacy grant rows without an audit trail.

Never silently backfill an audit event as though it were historical proof.
"""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.recovery_grant_audit_coverage import RecoveryGrantAuditCoverage


@dataclass(frozen=True)
class LegacyGrantReview:
    untracked_grants: tuple
    requires_manual_review: bool


class LegacyGrantReviewService:
    def __init__(self, database):
        self.coverage = RecoveryGrantAuditCoverage(database)

    def inspect(self):
        rows = tuple(self.coverage.inspect())
        return LegacyGrantReview(rows, bool(rows))
