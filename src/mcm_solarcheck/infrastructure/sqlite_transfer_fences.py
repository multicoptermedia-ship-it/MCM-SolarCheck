"""Monotonic transfer generations for cooperative workers.

A generation is only useful when the storage backend checks it atomically.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


class SQLiteTransferFences:
    def __init__(self, database: str | Path):
        self.database = str(database)
        with sqlite3.connect(self.database) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS transfer_fence_generations (
                transfer_id TEXT PRIMARY KEY,
                generation INTEGER NOT NULL CHECK (generation > 0)
            )""")

    def advance(self, transfer_id: str) -> int:
        if not isinstance(transfer_id, str) or not transfer_id or len(transfer_id) > 128:
            raise ValueError("invalid transfer id")
        with sqlite3.connect(self.database, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("""INSERT INTO transfer_fence_generations(transfer_id,generation)
                          VALUES (?,1)
                          ON CONFLICT(transfer_id) DO UPDATE
                          SET generation=generation+1""", (transfer_id,))
            return db.execute(
                "SELECT generation FROM transfer_fence_generations WHERE transfer_id=?",
                (transfer_id,)
            ).fetchone()[0]

    def is_current(self, transfer_id: str, generation: int) -> bool:
        if type(generation) is not int or generation <= 0:
            return False
        with sqlite3.connect(self.database) as db:
            row = db.execute(
                "SELECT generation FROM transfer_fence_generations WHERE transfer_id=?",
                (transfer_id,)
            ).fetchone()
        return row is not None and row[0] == generation
