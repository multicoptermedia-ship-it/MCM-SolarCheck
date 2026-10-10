"""Durable owner-scoped immutable part metadata; no publication side effects."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from mcm_solarcheck.services.immutable_upload_parts import immutable_part_key


class SQLiteImmutablePartManifest:
    def __init__(self, database: str | Path):
        self.database = str(database)
        with sqlite3.connect(self.database) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS immutable_upload_parts (
                transfer_id TEXT NOT NULL, customer_id TEXT NOT NULL,
                project_id TEXT NOT NULL, part_number INTEGER NOT NULL,
                sha256 TEXT NOT NULL, size INTEGER NOT NULL CHECK(size > 0),
                storage_key TEXT NOT NULL,
                PRIMARY KEY(transfer_id, part_number)
            )""")
            db.execute("""CREATE INDEX IF NOT EXISTS immutable_parts_owner
                          ON immutable_upload_parts(customer_id, project_id, transfer_id)""")

    def record(self, transfer_id: str, customer_id: str, project_id: str,
               part_number: int, digest: str, size: int) -> str:
        if any(not isinstance(x, str) or not x or "/" in x or "\\" in x or "\x00" in x
               for x in (customer_id, project_id)):
            raise ValueError("invalid owner")
        if type(size) is not int or size <= 0 or size > 8 * 1024 * 1024:
            raise ValueError("invalid part size")
        key = immutable_part_key(transfer_id, part_number, digest)
        with sqlite3.connect(self.database, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                """SELECT customer_id,project_id,sha256,size,storage_key
                   FROM immutable_upload_parts WHERE transfer_id=? AND part_number=?""",
                (transfer_id, part_number)).fetchone()
            expected = (customer_id, project_id, digest, size, key)
            if existing is not None:
                if existing != expected:
                    raise ValueError("conflicting immutable part")
                return key
            db.execute(
                """INSERT INTO immutable_upload_parts
                   (transfer_id,customer_id,project_id,part_number,sha256,size,storage_key)
                   VALUES (?,?,?,?,?,?,?)""",
                (transfer_id, customer_id, project_id, part_number, digest, size, key))
        return key

    def list_parts(self, transfer_id: str, customer_id: str, project_id: str) -> list[dict]:
        with sqlite3.connect(self.database) as db:
            rows = db.execute(
                """SELECT part_number,sha256,size,storage_key FROM immutable_upload_parts
                   WHERE transfer_id=? AND customer_id=? AND project_id=?
                   ORDER BY part_number""", (transfer_id, customer_id, project_id)).fetchall()
        return [dict(zip(("part_number", "sha256", "size", "storage_key"), row)) for row in rows]
