"""Atomic reservation of final local destination names in SQLite.

This is a journal-level uniqueness guard, not a distributed filesystem lock.
"""
from __future__ import annotations

import sqlite3


class SQLitePublicationDestinations:
    def __init__(self, database):
        self.database = str(database)
        with sqlite3.connect(self.database, timeout=30) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS publication_destinations (
                destination TEXT PRIMARY KEY,
                transfer_id TEXT NOT NULL UNIQUE,
                customer_id TEXT NOT NULL,
                project_id TEXT NOT NULL
            )""")

    def reserve(self, destination, transfer_id, customer_id, project_id):
        if not all(isinstance(v, str) and v for v in (destination, transfer_id, customer_id, project_id)):
            raise ValueError("invalid reservation")
        with sqlite3.connect(self.database, timeout=30) as db:
            db.execute("""INSERT OR IGNORE INTO publication_destinations
                (destination, transfer_id, customer_id, project_id) VALUES (?,?,?,?)""",
                (destination, transfer_id, customer_id, project_id))
            row = db.execute("""SELECT destination, transfer_id, customer_id, project_id
                FROM publication_destinations WHERE destination=? OR transfer_id=?""",
                (destination, transfer_id)).fetchall()
            if len(row) != 1 or row[0] != (destination, transfer_id, customer_id, project_id):
                raise ValueError("destination or transfer already reserved")
        return True

    def lookup(self, destination):
        with sqlite3.connect(self.database, timeout=30) as db:
            row = db.execute("""SELECT transfer_id, customer_id, project_id
                FROM publication_destinations WHERE destination=?""", (destination,)).fetchone()
        return row
