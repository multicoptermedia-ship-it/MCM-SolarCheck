"""Durable, owner-scoped metadata for interrupted staged transfers.

Metadata is not proof of remote bytes or permission to publish them.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class SQLiteTransferManifest:
    def __init__(self, database: str | Path):
        self.database = str(database)
        with sqlite3.connect(self.database) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS staged_transfer_manifests (
                transfer_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                final_key TEXT NOT NULL,
                staging_key TEXT NOT NULL UNIQUE,
                expected_size INTEGER NOT NULL CHECK(expected_size > 0),
                expected_sha256 TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('pending','verified','published','aborted')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL)""")
            db.execute("""CREATE INDEX IF NOT EXISTS idx_staged_transfer_owner
                          ON staged_transfer_manifests(customer_id, project_id, state)""")

    @staticmethod
    def _validate(customer_id, project_id, final_key, size, digest):
        for value in (customer_id, project_id):
            if not isinstance(value, str) or not value or value in (".", "..") or any(
                c in value for c in ("/", chr(92), chr(0))
            ):
                raise ValueError("invalid transfer owner")
        if not isinstance(final_key, str) or not final_key or final_key.startswith("/") or any(
            p in ("", ".", "..") for p in final_key.split("/")
        ) or chr(92) in final_key or chr(0) in final_key or final_key.startswith(".staging/"):
            raise ValueError("invalid final key")
        if type(size) is not int or size <= 0:
            raise ValueError("invalid expected size")
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("invalid SHA-256")

    def create(self, customer_id: str, project_id: str, final_key: str,
               expected_size: int, expected_sha256: str) -> str:
        self._validate(customer_id, project_id, final_key, expected_size, expected_sha256)
        transfer_id = uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.database) as db:
            db.execute("""INSERT INTO staged_transfer_manifests
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
                (transfer_id, customer_id, project_id, final_key,
                 ".staging/" + transfer_id, expected_size, expected_sha256, now, now))
        return transfer_id

    def get(self, transfer_id: str, customer_id: str, project_id: str):
        with sqlite3.connect(self.database) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("""SELECT * FROM staged_transfer_manifests
                WHERE transfer_id=? AND customer_id=? AND project_id=?""",
                (transfer_id, customer_id, project_id)).fetchone()
            return dict(row) if row is not None else None

    def transition(self, transfer_id: str, customer_id: str, project_id: str,
                   expected_state: str, next_state: str) -> bool:
        if (expected_state, next_state) not in {
            ("pending", "verified"), ("verified", "published"),
            ("pending", "aborted"), ("verified", "aborted")
        }:
            raise ValueError("invalid transfer state transition")
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.database) as db:
            result = db.execute("""UPDATE staged_transfer_manifests SET state=?, updated_at=?
                WHERE transfer_id=? AND customer_id=? AND project_id=? AND state=?""",
                (next_state, now, transfer_id, customer_id, project_id, expected_state))
            return result.rowcount == 1
