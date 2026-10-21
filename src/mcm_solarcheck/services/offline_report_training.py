"""Private offline report-linked training requests.

Training opt-in is strictly separate from expert report approval. A request
alone never grants customer rights, copies imagery or starts a model job.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from uuid import uuid4

from mcm_solarcheck.services.report_release import (
    ReportReleaseDecision, latest_release_decision,
)

NOTICE_VERSION = "offline-report-training-v1"


@dataclass(frozen=True)
class ReportTrainingRequest:
    request_id: str
    approval_id: int
    status: str
    sample_count: int = 0


class OfflineReportTraining:
    """Append-only intent ledger, privately scoped to the offline database."""

    def __init__(self, project_service, *, directory: str | Path | None = None,
                 training_launcher=None):
        from mcm_solarcheck.services.project_pipeline import ProjectApplicationService
        if not isinstance(project_service, ProjectApplicationService):
            raise TypeError("persisted offline project service required")
        self._service = project_service
        self._root = (
            Path(directory) if directory is not None
            else project_service.database.path.absolute().parent / "training-data"
        )
        self._launcher = training_launcher

    @property
    def _ledger(self) -> Path:
        return self._root / "report-training-requests.sqlite3"

    def _connect(self):
        # Created only after deliberate opt-in, never on ordinary app startup.
        self._root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self._root.is_symlink():
            raise PermissionError("training directory must not be linked")
        db = sqlite3.connect(self._ledger, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("""
            CREATE TABLE IF NOT EXISTS report_training_requests (
                request_id TEXT PRIMARY KEY,
                approval_id INTEGER NOT NULL,
                project_id TEXT NOT NULL,
                report_id TEXT NOT NULL,
                review_digest TEXT NOT NULL,
                authorized_by TEXT NOT NULL,
                rights_reference TEXT NOT NULL,
                notice_version TEXT NOT NULL,
                recorded_at_utc TEXT NOT NULL,
                status TEXT NOT NULL,
                sample_count INTEGER NOT NULL DEFAULT 0,
                UNIQUE(project_id,approval_id)
            )
        """)
        return db

    def request(self, *, project_id: str, report, approval: ReportReleaseDecision,
                authorized_by: str, rights_reference: str,
                affirmative_opt_in: bool = False) -> ReportTrainingRequest:
        """Record a fresh, signed-report-scoped training request; no implicit grant."""
        if affirmative_opt_in is not True:
            raise PermissionError("training opt-in must be actively checked")
        if not isinstance(project_id, str) or not project_id.strip():
            raise ValueError("project is required")
        if not isinstance(approval, ReportReleaseDecision):
            raise PermissionError("explicit report release required before training request")
        if not isinstance(authorized_by, str) or not (1 <= len(authorized_by.strip()) <= 120):
            raise ValueError("training approver identity required")
        if not isinstance(rights_reference, str) or not (3 <= len(rights_reference.strip()) <= 200):
            raise PermissionError("documented customer usage rights reference required")
        if any(ord(c) < 32 for c in rights_reference + authorized_by):
            raise ValueError("invalid control character in consent reference")
        if (approval.project_id != project_id or report.project_id != project_id
                or approval.report_id != report.report_id
                or approval.approved_by != authorized_by.strip()):
            raise PermissionError("training request does not match released report or reviewer")
        with self._service.database.connect() as sql:
            sql.execute("BEGIN IMMEDIATE")
            current = latest_release_decision(sql, report)
            if current is None or current != approval:
                raise PermissionError("report changed after approval")
            with self._connect() as db:
                stored = db.execute(
                    "SELECT request_id,status,sample_count FROM report_training_requests "
                    "WHERE project_id=? AND approval_id=?",
                    (project_id, approval.approval_id),
                ).fetchone()
                if stored is not None:
                    raise PermissionError("training opt-in already recorded for this approval")
                request_id = uuid4().hex
                db.execute(
                    """INSERT INTO report_training_requests
                    (request_id,approval_id,project_id,report_id,review_digest,
                     authorized_by,rights_reference,notice_version,recorded_at_utc,status)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (request_id, approval.approval_id, project_id, approval.report_id,
                     approval.review_digest, authorized_by.strip(), rights_reference.strip(),
                     NOTICE_VERSION, datetime.now(timezone.utc).isoformat(),
                     "pending_training_data_review"),
                )
                db.commit()
        return ReportTrainingRequest(request_id, approval.approval_id,
                                     "pending_training_data_review")

    def state(self, project_id: str, approval_id: int) -> ReportTrainingRequest | None:
        """Non-creating read: inspection/release without opt-in leaves no ledger."""
        if not self._ledger.is_file():
            return None
        db = sqlite3.connect(self._ledger)
        try:
            row = db.execute(
                "SELECT request_id,approval_id,status,sample_count "
                "FROM report_training_requests WHERE project_id=? AND approval_id=?",
                (project_id, approval_id),
            ).fetchone()
            return ReportTrainingRequest(*row) if row else None
        finally:
            db.close()
