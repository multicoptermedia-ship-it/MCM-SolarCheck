"""SQLite audit records for operator recovery decisions; authentication is external."""
import sqlite3
from datetime import datetime, timezone


class SQLiteRecoveryAudit:
    def __init__(self, database):
        self.database = str(database)
        with sqlite3.connect(self.database) as db:
            db.execute("CREATE TABLE IF NOT EXISTS recovery_events (id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, transfer_id TEXT NOT NULL, customer_id TEXT NOT NULL, project_id TEXT NOT NULL, operator_id TEXT NOT NULL, decision TEXT NOT NULL)")

    def record(self, transfer_id, customer_id, project_id, operator_id, decision):
        fields = (transfer_id, customer_id, project_id, operator_id, decision)
        if not all(isinstance(v, str) and 0 < len(v) <= 256 for v in fields):
            raise ValueError("invalid recovery audit fields")
        with sqlite3.connect(self.database) as db:
            result = db.execute("INSERT INTO recovery_events (timestamp, transfer_id, customer_id, project_id, operator_id, decision) VALUES (?,?,?,?,?,?)", (datetime.now(timezone.utc).isoformat(), *fields))
            return result.lastrowid

    def list_for_transfer(self, transfer_id, customer_id, project_id):
        with sqlite3.connect(self.database) as db:
            rows = db.execute("SELECT timestamp, operator_id, decision FROM recovery_events WHERE transfer_id=? AND customer_id=? AND project_id=? ORDER BY id", (transfer_id, customer_id, project_id)).fetchall()
        return rows
