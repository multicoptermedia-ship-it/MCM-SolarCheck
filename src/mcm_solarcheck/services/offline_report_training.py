"""Private offline report-linked training requests.

Training opt-in is strictly separate from expert report approval. A request
alone never grants customer rights, copies imagery or starts a model job.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import shutil
import stat
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
                 training_launcher=None, training_configuration=None):
        from mcm_solarcheck.services.project_pipeline import ProjectApplicationService
        if not isinstance(project_service, ProjectApplicationService):
            raise TypeError("persisted offline project service required")
        self._service = project_service
        self._root = (
            Path(directory) if directory is not None
            else project_service.database.path.absolute().parent / "training-data"
        )
        self._launcher = training_launcher
        self._training_jobs = None
        if training_launcher is not None or training_configuration is not None:
            from mcm_solarcheck.services.offline_training_jobs import OfflineTrainingJobs
            self._training_jobs = OfflineTrainingJobs(
                self._root, self._ledger, training_configuration, training_launcher,
            )

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
        result = ReportTrainingRequest(request_id, approval.approval_id,
                                       "pending_training_data_review")
        # The report remains signed even if training intake is unavailable.
        # A request is NOT a started training job.
        try:
            result = self.stage_if_eligible(project_id, report, approval, result)
            if result.status == "staged_waiting_for_trainer" and self._training_jobs:
                try:
                    if self._training_jobs.launch(
                        project_id=project_id, request_id=request_id,
                    ):
                        return ReportTrainingRequest(
                            request_id, approval.approval_id, "training_running",
                            result.sample_count,
                        )
                except (OSError, ValueError, PermissionError, TypeError):
                    # Missing/invalid model or insufficient train/val/test
                    # leaves the signed report untouched and the data waiting.
                    pass
            return result
        except (OSError, ValueError, PermissionError, KeyError, TypeError):
            return result

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


    def stage_if_eligible(self, project_id: str, report,
                          approval: ReportReleaseDecision,
                          request: ReportTrainingRequest) -> ReportTrainingRequest:
        """Stage only *all* already-reviewed and rights-approved training samples.

        No source file or customer identity is put into a public manifest. This
        boundary deliberately does not launch Ultralytics absent a validated
        offline model, version/weights/license, split and training policy.
        """
        from mcm_solarcheck.review.training_snapshot import build_training_snapshot
        from mcm_solarcheck.review.dataset_build import build_dataset

        if request.status != "pending_training_data_review":
            return request
        with self._service.database.connect() as sql:
            sql.execute("BEGIN IMMEDIATE")
            if latest_release_decision(sql, report) != approval:
                raise PermissionError("report release is stale")
            original = self._service.database.training_samples(project_id)
            if not original or any(
                x["rights_status"] != "approved" or x["label_status"] != "human_reviewed"
                for x in original
            ):
                return request
            snapshot = build_training_snapshot(self._service.database, project_id)
            if snapshot.sample_count != len(original) or snapshot.label_count < 1:
                return request
            try:
                dataset = build_dataset(snapshot)
            except (ValueError, FileNotFoundError):
                return request
            if dataset.sample_count != snapshot.label_count:
                # Unlabeled and partially reviewed samples cannot silently enter.
                return request
            rows = json.loads(dataset.manifest_json)["rows"]
            if len(rows) > 1500:
                raise ValueError("training request exceeds local file count cap")
            folder = self._root / request.request_id
            if folder.exists() or folder.is_symlink():
                raise PermissionError("training snapshot destination already exists")
            folder.mkdir(mode=0o700)
            total = 0
            manifest = []
            try:
                for index, row in enumerate(rows):
                    source = Path(row["source_file"])
                    if source.is_symlink() or not source.is_file():
                        raise PermissionError("training source missing or linked")
                    size = source.stat().st_size
                    if not 0 < size <= 25_000_000 or total + size > 250_000_000:
                        raise ValueError("training image size cap exceeded")
                    extension = source.suffix.lower()
                    if extension not in (".jpg", ".jpeg", ".png", ".tif", ".tiff"):
                        raise ValueError("training image extension not supported")
                    output = f"sample-{index:05d}{extension}"
                    digest = hashlib.sha256()
                    fd = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
                    try:
                        with os.fdopen(fd, "rb") as source_handle, (folder / output).open("xb") as dest:
                            if not stat.S_ISREG(os.fstat(source_handle.fileno()).st_mode):
                                raise PermissionError("training source is not regular")
                            copied = 0
                            while chunk := source_handle.read(1024 * 1024):
                                copied += len(chunk)
                                if copied > 25_000_000 or total + copied > 250_000_000:
                                    raise ValueError("training image grew during copy")
                                dest.write(chunk)
                                digest.update(chunk)
                            dest.flush()
                            os.fsync(dest.fileno())
                    finally:
                        pass
                    if copied != size or digest.hexdigest() != row["content_sha256"]:
                        raise ValueError("training source changed since review")
                    total += copied
                    group = (row.get("inspection_group_id")
                             or row.get("module_id") or row.get("finding_id"))
                    if not isinstance(group, str) or not group.strip():
                        raise ValueError("training image needs reviewed physical group")
                    group_key = hashlib.sha256(
                        (request.request_id + ":" + group).encode("utf-8")
                    ).hexdigest()
                    manifest.append({
                        "image": output, "sha256": digest.hexdigest(),
                        "modality": row["modality"],
                        "defect_class": row["defect_class"],
                        "split": row["split"],
                        "inspection_group_key": group_key,
                    })
                (folder / "training-index.json").write_text(
                    json.dumps({"dataset_id": dataset.dataset_id,
                                "samples": manifest}, sort_keys=True),
                    encoding="utf-8",
                )
                if latest_release_decision(sql, report) != approval:
                    raise PermissionError("report release changed while staging")
                with self._connect() as ledger:
                    ledger.execute("BEGIN IMMEDIATE")
                    changed = ledger.execute(
                        """UPDATE report_training_requests
                        SET status='staged_waiting_for_trainer',sample_count=?
                        WHERE project_id=? AND request_id=?
                          AND status='pending_training_data_review'""",
                        (len(manifest), project_id, request.request_id),
                    ).rowcount
                    if changed != 1:
                        raise PermissionError("training request changed during staging")
                    ledger.commit()
                return ReportTrainingRequest(request.request_id, approval.approval_id,
                                             "staged_waiting_for_trainer", len(manifest))
            except BaseException:
                shutil.rmtree(folder, ignore_errors=True)
                raise

    def revoke(self, project_id: str, approval_id: int) -> None:
        """Stop future use and erase staged copies. Cannot untrain an existing model."""
        current = self.state(project_id, approval_id)
        if current is None:
            return
        with self._connect() as ledger:
            ledger.execute("BEGIN IMMEDIATE")
            changed = ledger.execute(
                """UPDATE report_training_requests SET status='revoked'
                WHERE project_id=? AND approval_id=? AND status != 'revoked'""",
                (project_id, approval_id),
            ).rowcount
            ledger.commit()
        running = (
            self._training_jobs.cancel(current.request_id)
            if self._training_jobs is not None else False
        )
        if changed and not running:
            folder = self._root / current.request_id
            if folder.is_dir() and not folder.is_symlink():
                shutil.rmtree(folder)
