"""Durable owner-scoped journal for local publication attempts.

This journal does not itself make publication atomic with a filesystem write.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


class SQLitePublicationJournal:
    STATES = {"prepared", "publishing", "published", "needs_review"}

    def __init__(self, database):
        self.database = str(database)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS local_publications (
                transfer_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                destination TEXT NOT NULL,
                expected_size INTEGER NOT NULL CHECK(expected_size > 0),
                expected_sha256 TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('prepared','publishing','published','needs_review'))
            )""")

    def _connect(self):
        return sqlite3.connect(self.database, timeout=30)

    def prepare(self, transfer_id, customer_id, project_id, destination, expected_size, expected_sha256):
        if not all(isinstance(x, str) and x for x in (transfer_id, customer_id, project_id, destination)):
            raise ValueError("missing publication identity")
        if type(expected_size) is not int or expected_size <= 0:
            raise ValueError("invalid size")
        if (not isinstance(expected_sha256, str) or len(expected_sha256) != 64
                or any(x not in "0123456789abcdef" for x in expected_sha256)):
            raise ValueError("invalid hash")
        with self._connect() as db:
            db.execute("""INSERT OR IGNORE INTO local_publications
                (transfer_id, customer_id, project_id, destination, expected_size, expected_sha256, state)
                VALUES (?,?,?,?,?,?,'prepared')""",
                (transfer_id, customer_id, project_id, destination, expected_size, expected_sha256))
            row = db.execute("""SELECT customer_id, project_id, destination, expected_size, expected_sha256
                FROM local_publications WHERE transfer_id=?""", (transfer_id,)).fetchone()
            if row != (customer_id, project_id, destination, expected_size, expected_sha256):
                raise ValueError("conflicting publication attempt")
        return self.get(transfer_id, customer_id, project_id)

    def get(self, transfer_id, customer_id, project_id):
        with self._connect() as db:
            row = db.execute("""SELECT destination, expected_size, expected_sha256, state
                FROM local_publications WHERE transfer_id=? AND customer_id=? AND project_id=?""",
                (transfer_id, customer_id, project_id)).fetchone()
        if row is None:
            return None
        return dict(zip(("destination", "expected_size", "expected_sha256", "state"), row))

    def transition(self, transfer_id, customer_id, project_id, expected_state, next_state):
        if (expected_state, next_state) not in {
            ("prepared", "publishing"), ("publishing", "published"),
            ("publishing", "needs_review"), ("needs_review", "published")
        }:
            raise ValueError("unsupported state transition")
        with self._connect() as db:
            result = db.execute("""UPDATE local_publications SET state=?
                WHERE transfer_id=? AND customer_id=? AND project_id=? AND state=?""",
                (next_state, transfer_id, customer_id, project_id, expected_state))
            return result.rowcount == 1
