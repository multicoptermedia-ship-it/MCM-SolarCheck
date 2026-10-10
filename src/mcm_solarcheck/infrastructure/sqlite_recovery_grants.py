"""Legacy read-only recovery grant lookup.

Unaudited writes have been disabled. Use AuthorizedGrantAdministration with
SQLiteAuditedRecoveryGrants for all changes.
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
        raise PermissionError(
            "legacy unaudited grant writes disabled; use AuthorizedGrantAdministration"
        )

    def allowed(self, operator_id, customer_id, project_id):
        with sqlite3.connect(self.database) as db:
            row = db.execute("""SELECT enabled FROM recovery_grants
                WHERE operator_id=? AND customer_id=? AND project_id=?""",
                (operator_id, customer_id, project_id)).fetchone()
        return row is not None and row[0] == 1
