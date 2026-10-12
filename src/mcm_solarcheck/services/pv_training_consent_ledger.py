"""Local SQLite opt-in/revocation ledger, separate from exported training pixels."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from uuid import uuid4


@dataclass(frozen=True)
class TrainingConsentState:
    project_key: str
    active: bool
    consent_reference: str | None


class TrainingConsentLedger:
    def __init__(self, database: Path):
        self.database = Path(database)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS training_consent_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_key TEXT NOT NULL,
                action TEXT NOT NULL CHECK(action IN ('grant', 'revoke')),
                reference TEXT NOT NULL UNIQUE,
                recorded_at TEXT NOT NULL
            )""")

    def _connect(self):
        return sqlite3.connect(self.database, timeout=10)

    def _record(self, project_key: str, action: str) -> str:
        if not isinstance(project_key, str) or not project_key.strip():
            raise ValueError("private project key required")
        reference = uuid4().hex
        with self._connect() as db:
            db.execute(
                "INSERT INTO training_consent_events(project_key,action,reference,recorded_at) VALUES (?,?,?,?)",
                (project_key, action, reference, datetime.now(timezone.utc).isoformat()),
            )
        return reference

    def grant(self, project_key: str, *, affirmative_opt_in: bool = False) -> str:
        if affirmative_opt_in is not True:
            raise PermissionError("unchecked by default: explicit opt-in required")
        return self._record(project_key, "grant")

    def revoke(self, project_key: str) -> str:
        return self._record(project_key, "revoke")

    def current(self, project_key: str) -> TrainingConsentState:
        if not isinstance(project_key, str) or not project_key.strip():
            raise ValueError("private project key required")
        with self._connect() as db:
            row = db.execute(
                "SELECT action, reference FROM training_consent_events WHERE project_key=? ORDER BY id DESC LIMIT 1",
                (project_key,),
            ).fetchone()
        return TrainingConsentState(project_key, bool(row and row[0] == "grant"),
                                    row[1] if row and row[0] == "grant" else None)

    def require_active(self, project_key: str, consent_reference: str) -> None:
        state = self.current(project_key)
        if not state.active or state.consent_reference != consent_reference:
            raise PermissionError("training consent missing, superseded or revoked")
