"""Read-only detection of grant rows with no corresponding audit history.

An unaudited row is not proof of malicious modification: it may predate audit.
"""
from __future__ import annotations

import sqlite3


class RecoveryGrantAuditCoverage:
    def __init__(self, database):
        self.database = str(database)

    def inspect(self):
        with sqlite3.connect(self.database) as db:
            rows = db.execute("""SELECT g.operator_id,g.customer_id,g.project_id,g.enabled
                FROM recovery_grants AS g
                WHERE NOT EXISTS (
                    SELECT 1 FROM recovery_grant_events AS e
                    WHERE e.operator_id=g.operator_id
                      AND e.customer_id=g.customer_id
                      AND e.project_id=g.project_id
                )
                ORDER BY g.operator_id,g.customer_id,g.project_id""").fetchall()
        return rows
