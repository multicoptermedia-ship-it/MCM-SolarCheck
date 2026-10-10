"""Request-scoped append-only audit events for explicit recovery."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


class SQLiteRequestRecoveryAudit:
    def __init__(self, database):
        self.database = str(database)
        with sqlite3.connect(self.database) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS request_recovery_events (
                id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL,
                request_id TEXT NOT NULL, transfer_id TEXT NOT NULL,
                customer_id TEXT NOT NULL, project_id TEXT NOT NULL,
                operator_id TEXT NOT NULL, decision TEXT NOT NULL
            )""")

    def record(self, request_id, transfer_id, customer_id, project_id, operator_id, decision):
        fields = (request_id, transfer_id, customer_id, project_id, operator_id, decision)
        if not all(isinstance(v, str) and 0 < len(v) <= 256 for v in fields):
            raise ValueError("invalid request audit fields")
        with sqlite3.connect(self.database) as db:
            cursor = db.execute("""INSERT INTO request_recovery_events
                (timestamp,request_id,transfer_id,customer_id,project_id,operator_id,decision)
                VALUES (?,?,?,?,?,?,?)""",
                (datetime.now(timezone.utc).isoformat(), *fields))
            return cursor.lastrowid

    def list_for_request(self, request_id, transfer_id, customer_id, project_id, operator_id):
        with sqlite3.connect(self.database) as db:
            return db.execute("""SELECT timestamp,decision FROM request_recovery_events
                WHERE request_id=? AND transfer_id=? AND customer_id=? AND project_id=? AND operator_id=?
                ORDER BY id""",
                (request_id, transfer_id, customer_id, project_id, operator_id)).fetchall()
