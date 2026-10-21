"""Explicit, append-only local expert report decisions.

No decision is inferred from review percentage or a rendered PDF. The digest
binds the decision to the report and all persisted project inspection records.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import sqlite3

from mcm_solarcheck.reporting.report_model import InspectionReport
from mcm_solarcheck.services.review_progress import ReviewProgress


# Project tables that can affect the human interpretation of a report.
_EVIDENCE_TABLES = (
    "projects", "project_profiles", "image_frames", "thermal_frames",
    "image_pairs", "pv_modules", "module_identity_links", "findings",
    "finding_sensor_links", "finding_reviews", "project_geotiffs",
)


@dataclass(frozen=True)
class ReportReleaseDecision:
    approval_id: int
    project_id: str
    report_id: str
    inspection_started_utc: str
    approved_by: str
    approved_at_utc: str
    review_digest: str
    unclear_count: int
    followup_note: str


def _inspection_time(report: InspectionReport) -> str:
    return report.inspection_started_at.astimezone(timezone.utc).isoformat()


def report_release_digest(sql: sqlite3.Connection, report: InspectionReport) -> str:
    """Hash the model and all current project evidence in deterministic order.

    Never store source paths, customers or other private evidence in the audit
    digest. Hashing is not digital signing or proof of external file provenance.
    """
    if not isinstance(report, InspectionReport):
        raise TypeError("inspection report required")
    digest = hashlib.sha256()
    digest.update(repr(report).encode("utf-8"))
    for table in _EVIDENCE_TABLES:
        digest.update(table.encode("ascii"))
        for row in sql.execute(
            f"SELECT * FROM {table} WHERE project_id=? ORDER BY rowid",
            (report.project_id,),
        ):
            data = json.dumps(tuple(row), ensure_ascii=False, separators=(",", ":"),
                              default=str)
            digest.update(data.encode("utf-8"))
            digest.update(b"\n")
    return digest.hexdigest()


def require_release_review(progress: ReviewProgress, *,
                           acknowledge_unclear: bool, followup_note: str) -> None:
    """Conservatively reject missing/undecided evidence and silent unclear review."""
    if not isinstance(progress, ReviewProgress):
        raise TypeError("persisted review progress required")
    if progress.total_findings == 0:
        raise ValueError("no findings: inspection completeness not evidenced")
    if not progress.all_findings_decided or progress.other_status_findings:
        raise ValueError("all findings require explicit known expert decisions")
    if progress.unclear_findings and (
        acknowledge_unclear is not True or not isinstance(followup_note, str)
        or not followup_note.strip()
    ):
        raise ValueError("unclear findings require acknowledged follow-up note")


def latest_release_decision(sql: sqlite3.Connection, report: InspectionReport
                            ) -> ReportReleaseDecision | None:
    """A stored sign-off is usable only while its full project snapshot matches."""
    row = sql.execute(
        """SELECT approval_id,project_id,report_id,inspection_started_utc,
                  approved_by,approved_at_utc,review_digest,unclear_count,followup_note
           FROM report_release_decisions WHERE project_id=? AND report_id=?
           ORDER BY approval_id DESC LIMIT 1""",
        (report.project_id, report.report_id),
    ).fetchone()
    if row is None:
        return None
    decision = ReportReleaseDecision(*tuple(row))
    if (decision.inspection_started_utc != _inspection_time(report)
            or decision.review_digest != report_release_digest(sql, report)):
        return None
    return decision


def record_release_decision(
    sql: sqlite3.Connection, report: InspectionReport, progress: ReviewProgress, *,
    approved_by: str, acknowledge_unclear: bool = False, followup_note: str = "",
) -> ReportReleaseDecision:
    """Call only within a BEGIN IMMEDIATE transaction after workflow checks."""
    if report.release_status != "draft" or report.project_id != progress.project_id:
        raise ValueError("draft/project mismatch")
    if not isinstance(approved_by, str) or not (1 <= len(approved_by.strip()) <= 120):
        raise ValueError("explicit expert name is required")
    if any(ord(ch) < 32 for ch in approved_by):
        raise ValueError("invalid reviewer identifier")
    if not isinstance(followup_note, str) or len(followup_note) > 2000:
        raise ValueError("invalid follow-up note")
    require_release_review(
        progress, acknowledge_unclear=acknowledge_unclear,
        followup_note=followup_note,
    )
    digest = report_release_digest(sql, report)
    approved_at = datetime.now(timezone.utc).isoformat()
    cursor = sql.execute(
        """INSERT INTO report_release_decisions
           (project_id,report_id,inspection_started_utc,approved_by,approved_at_utc,
            review_digest,unclear_count,followup_note)
           VALUES (?,?,?,?,?,?,?,?)""",
        (report.project_id, report.report_id, _inspection_time(report),
         approved_by.strip(), approved_at, digest, progress.unclear_findings,
         followup_note.strip()),
    )
    return ReportReleaseDecision(
        cursor.lastrowid, report.project_id, report.report_id,
        _inspection_time(report), approved_by.strip(), approved_at, digest,
        progress.unclear_findings, followup_note.strip(),
    )
