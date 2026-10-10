"""Durable, fail-closed idempotency claims for explicit recovery attempts."""
from __future__ import annotations

import sqlite3


class SQLiteRecoveryAttempts:
    def __init__(self, database):
        self.database = str(database)
        with sqlite3.connect(self.database, timeout=30) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS recovery_attempts (
                request_id TEXT PRIMARY KEY,
                transfer_id TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                operator_id TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('pending','completed')),
                outcome TEXT
            )""")

    def claim(self, request_id, transfer_id, customer_id, project_id, operator_id):
        fields = (request_id, transfer_id, customer_id, project_id, operator_id)
        if not all(isinstance(v, str) and 0 < len(v) <= 256 for v in fields):
            raise ValueError("invalid recovery request identity")
        with sqlite3.connect(self.database, timeout=30) as db:
            db.execute("""INSERT OR IGNORE INTO recovery_attempts
                (request_id,transfer_id,customer_id,project_id,operator_id,state,outcome)
                VALUES (?,?,?,?,?,'pending',NULL)""", fields)
            row = db.execute("""SELECT transfer_id,customer_id,project_id,operator_id,state,outcome
                FROM recovery_attempts WHERE request_id=?""", (request_id,)).fetchone()
        if row[:4] != fields[1:]:
            return ("identity_conflict", None)
        return (row[4], row[5])

    def complete(self, request_id, transfer_id, customer_id, project_id, operator_id, outcome):
        if not isinstance(outcome, str) or not 0 < len(outcome) <= 256:
            raise ValueError("invalid recovery outcome")
        with sqlite3.connect(self.database, timeout=30) as db:
            updated = db.execute("""UPDATE recovery_attempts SET state='completed', outcome=?
                WHERE request_id=? AND transfer_id=? AND customer_id=? AND project_id=?
                AND operator_id=? AND state='pending'""",
                (outcome, request_id, transfer_id, customer_id, project_id, operator_id))
            return updated.rowcount == 1

    def inspect(self, request_id, transfer_id, customer_id, project_id, operator_id):
        with sqlite3.connect(self.database, timeout=30) as db:
            row = db.execute("""SELECT state,outcome FROM recovery_attempts
                WHERE request_id=? AND transfer_id=? AND customer_id=? AND project_id=? AND operator_id=?""",
                (request_id, transfer_id, customer_id, project_id, operator_id)).fetchone()
        return row
