"""Cooperative background execution of explicitly configured local AI trainers.

No default trainer, model download, update check or auto-deployment. A trainer
is an operator-installed, separately validated backend callable; it must obey
cancellation and must not use the network. Starting is strictly conditional
on immutable local model checks and reviewed classification dataset splits.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import shutil
import sqlite3
from threading import Event, Lock, Thread

from mcm_solarcheck.services.offline_training_preflight import (
    OfflineTrainerConfiguration, verify_staged_classification_dataset,
)


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class TrainingCancelled(Exception):
    """The caller revoked or cancelled an active offline training run."""


class OfflineTrainingJobs:
    def __init__(self, root: Path, ledger: Path, config: OfflineTrainerConfiguration,
                 launcher):
        if not isinstance(config, OfflineTrainerConfiguration) or not callable(launcher):
            raise TypeError("explicit validated trainer configuration and backend required")
        self.root = root
        self.ledger = ledger
        self.config = config
        self.launcher = launcher
        self._cancel: dict[str, Event] = {}
        self._guard = Lock()

    def _connect(self):
        db = sqlite3.connect(self.ledger, timeout=10)
        db.execute("""CREATE TABLE IF NOT EXISTS report_training_job_progress (
            request_id TEXT PRIMARY KEY, updated_at TEXT NOT NULL,
            percent INTEGER NOT NULL DEFAULT 0 CHECK(percent BETWEEN 0 AND 100),
            weights_sha256 TEXT, error_code TEXT
        )""")
        return db

    def is_active(self, request_id: str) -> bool:
        with self._guard:
            return request_id in self._cancel

    def launch(self, *, project_id: str, request_id: str) -> bool:
        """Compare-and-set before starting; return False when no job can start."""
        self.config.verify_model()
        dataset_dir = self.root / request_id
        verified = verify_staged_classification_dataset(dataset_dir)
        with self._guard:
            if request_id in self._cancel:
                return False
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                updated = db.execute(
                    """UPDATE report_training_requests SET status='training_running'
                    WHERE project_id=? AND request_id=?
                      AND status='staged_waiting_for_trainer'""",
                    (project_id, request_id),
                ).rowcount
                if updated != 1:
                    return False
                db.execute(
                    """INSERT INTO report_training_job_progress
                       (request_id,updated_at,percent) VALUES (?,?,0)""",
                    (request_id, _utc()),
                )
            event = Event()
            self._cancel[request_id] = event
            try:
                thread = Thread(
                    target=self._worker,
                    args=(project_id, request_id, verified, event),
                    name="solarcheck-local-training", daemon=True,
                )
                thread.start()
            except BaseException:
                self._cancel.pop(request_id, None)
                with self._connect() as db:
                    db.execute(
                        "UPDATE report_training_requests SET status='staged_waiting_for_trainer' "
                        "WHERE request_id=? AND status='training_running'",
                        (request_id,),
                    )
                    db.execute("DELETE FROM report_training_job_progress WHERE request_id=?",
                               (request_id,))
                raise
        return True

    def cancel(self, request_id: str) -> bool:
        """Signal a cooperative trainer; do not pretend a live thread stopped."""
        with self._guard:
            event = self._cancel.get(request_id)
            if event is not None:
                event.set()
            return event is not None

    def _progress(self, request_id: str, event: Event, percent: int) -> None:
        if event.is_set():
            raise TrainingCancelled()
        if type(percent) is not int or not 0 <= percent <= 99:
            raise ValueError("invalid training progress")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT status FROM report_training_requests WHERE request_id=?",
                (request_id,),
            ).fetchone()
            if row is None or row[0] != "training_running":
                raise TrainingCancelled()
            db.execute(
                """UPDATE report_training_job_progress SET percent=?,updated_at=?
                   WHERE request_id=?""", (percent, _utc(), request_id),
            )

    def _worker(self, project_id, request_id, verified, event: Event) -> None:
        outcome = "training_failed"
        error_code = "backend_failure"
        weights_sha = None
        folder = self.root / request_id
        output = folder / "trained"
        try:
            if event.is_set():
                raise TrainingCancelled()
            # A trainer receives only the reviewed private folder and config.
            # No customer IDs, contact details, source paths or network handles.
            output.mkdir(mode=0o700)
            target = self.launcher(
                verified, self.config, output,
                lambda percent: self._progress(request_id, event, percent),
                event,
            )
            if event.is_set():
                raise TrainingCancelled()
            result = Path(target)
            if (result.is_symlink() or not result.is_file()
                    or result.suffix.lower() != ".pt"
                    or result.resolve().parent != output.resolve()
                    or not 0 < result.stat().st_size <= 500_000_000):
                raise ValueError("trainer output invalid")
            weights_sha = sha256(result.read_bytes()).hexdigest()
            # Commit only an actual artifact in a private local directory.
            outcome = "training_completed_not_deployed"
            error_code = None
        except TrainingCancelled:
            outcome = "training_cancelled"
            error_code = None
        except BaseException:
            # Never publish exception text: file paths may contain customer data.
            error_code = "trainer_failed_or_invalid_output"
        finally:
            try:
                with self._connect() as db:
                    db.execute("BEGIN IMMEDIATE")
                    status = db.execute(
                        "SELECT status FROM report_training_requests WHERE request_id=? "
                        "AND project_id=?", (request_id, project_id),
                    ).fetchone()
                    revoked = status is None or status[0] == "revoked"
                    if revoked or event.is_set():
                        outcome, error_code, weights_sha = "training_cancelled", None, None
                    if not revoked:
                        db.execute(
                            """UPDATE report_training_requests SET status=?
                               WHERE project_id=? AND request_id=?
                                 AND status='training_running'""",
                            (outcome, project_id, request_id),
                        )
                    db.execute(
                        """UPDATE report_training_job_progress
                           SET percent=?,updated_at=?,weights_sha256=?,error_code=?
                           WHERE request_id=?""",
                        (100 if outcome == "training_completed_not_deployed" else 0,
                         _utc(), weights_sha, error_code, request_id),
                    )
                if revoked or event.is_set():
                    shutil.rmtree(folder, ignore_errors=True)
            finally:
                with self._guard:
                    self._cancel.pop(request_id, None)
