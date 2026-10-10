"""Transactional grant changes and append-only audit in one SQLite database.

Only trusted administrative code should call set_grant; no public endpoint.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


class SQLiteAuditedRecoveryGrants:
    def __init__(self, database):
        self.database = str(database)
        with sqlite3.connect(self.database) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS recovery_grants (
                operator_id TEXT NOT NULL, customer_id TEXT NOT NULL,
                project_id TEXT NOT NULL, enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),
                PRIMARY KEY(operator_id,customer_id,project_id)
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS recovery_grant_events (
                id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL,
                actor_id TEXT NOT NULL, operator_id TEXT NOT NULL,
                customer_id TEXT NOT NULL, project_id TEXT NOT NULL,
                previous_enabled INTEGER, next_enabled INTEGER NOT NULL
            )""")

    def set_grant(self, actor_id, operator_id, customer_id, project_id, enabled):
        fields = (actor_id, operator_id, customer_id, project_id)
        if not all(isinstance(v, str) and 0 < len(v) <= 256 for v in fields):
            raise ValueError("invalid actor or grant identity")
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be boolean")
        with sqlite3.connect(self.database, timeout=30) as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("""SELECT enabled FROM recovery_grants
                WHERE operator_id=? AND customer_id=? AND project_id=?""",
                (operator_id, customer_id, project_id)).fetchone()
            db.execute("""INSERT INTO recovery_grants(operator_id,customer_id,project_id,enabled)
                VALUES(?,?,?,?) ON CONFLICT(operator_id,customer_id,project_id)
                DO UPDATE SET enabled=excluded.enabled""",
                (operator_id, customer_id, project_id, int(enabled)))
            db.execute("""INSERT INTO recovery_grant_events
                (timestamp,actor_id,operator_id,customer_id,project_id,previous_enabled,next_enabled)
                VALUES(?,?,?,?,?,?,?)""",
                (datetime.now(timezone.utc).isoformat(), *fields,
                 None if previous is None else previous[0], int(enabled)))

    def allowed(self, operator_id, customer_id, project_id):
        with sqlite3.connect(self.database) as db:
            row = db.execute("""SELECT enabled FROM recovery_grants
                WHERE operator_id=? AND customer_id=? AND project_id=?""",
                (operator_id, customer_id, project_id)).fetchone()
        return row is not None and row[0] == 1

    def list_events(self, operator_id, customer_id, project_id):
        with sqlite3.connect(self.database) as db:
            return db.execute("""SELECT timestamp,actor_id,previous_enabled,next_enabled
                FROM recovery_grant_events WHERE operator_id=? AND customer_id=? AND project_id=?
                ORDER BY id""", (operator_id, customer_id, project_id)).fetchall()
