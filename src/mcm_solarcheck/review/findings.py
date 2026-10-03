"""Expert review workflow for AI/rule-generated inspection findings."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum

from mcm_solarcheck.domain.models import Finding


class ReviewStatus(str, Enum):
    UNREVIEWED = "unreviewed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    UNCLEAR = "unclear"


@dataclass(frozen=True)
class FindingReview:
    finding_id: str
    status: ReviewStatus
    reviewer: str
    reviewed_at_utc: datetime
    note: str | None = None


def review_finding(
    finding: Finding,
    *,
    status: ReviewStatus,
    reviewer: str,
    note: str | None = None,
    reviewed_at_utc: datetime | None = None,
) -> tuple[Finding, FindingReview]:
    """Apply an explicit human decision while retaining machine evidence."""
    reviewer = reviewer.strip()
    if not reviewer:
        raise ValueError("reviewer must not be empty")
    if status == ReviewStatus.UNREVIEWED:
        raise ValueError("a completed review cannot set status back to unreviewed")
    when = reviewed_at_utc or datetime.now(timezone.utc)
    if when.tzinfo is None:
        raise ValueError("review timestamp must be timezone-aware")
    metadata = dict(finding.metadata)
    metadata["review_source"] = "human"
    reviewed = replace(finding, reviewer_status=status.value, metadata=metadata)
    audit = FindingReview(finding.finding_id, status, reviewer, when.astimezone(timezone.utc), note)
    return reviewed, audit
