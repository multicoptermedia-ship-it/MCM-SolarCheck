"""Optional owner-scoped operator grants for recovery permissions.

Trusted caller must authenticate the operator independently. No self-service grants.
"""
from __future__ import annotations

import sqlite3


class SQLiteRecoveryGrants:
    def __init__(self, database):
        self.database = str(database)
        with sqlite3.connect(self.database) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS recovery_grants (
                operator_id TEXT NOT NULL, customer_id TEXT NOT NULL,
                project_id TEXT NOT NULL, enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),
                PRIMARY KEY(operator_id,customer_id,project_id)
            )""")

    def set_grant(self, operator_id, customer_id, project_id, enabled):
        fields = (operator_id, customer_id, project_id)
        if not all(isinstance(v, str) and 0 < len(v) <= 256 for v in fields):
            raise ValueError("invalid recovery grant identity")
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be boolean")
        with sqlite3.connect(self.database) as db:
            db.execute("""INSERT INTO recovery_grants(operator_id,customer_id,project_id,enabled)
                VALUES(?,?,?,?) ON CONFLICT(operator_id,customer_id,project_id)
                DO UPDATE SET enabled=excluded.enabled""", (*fields, int(enabled)))

    def allowed(self, operator_id, customer_id, project_id):
        with sqlite3.connect(self.database) as db:
            row = db.execute("""SELECT enabled FROM recovery_grants
                WHERE operator_id=? AND customer_id=? AND project_id=?""",
                (operator_id, customer_id, project_id)).fetchone()
        return row is not None and row[0] == 1
