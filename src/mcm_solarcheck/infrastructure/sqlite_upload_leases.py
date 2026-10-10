"""SQLite-backed coordination leases for cooperating upload workers."""
from __future__ import annotations

import sqlite3
import time
import threading
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


class UploadLeaseBusy(RuntimeError):
    pass


class UploadLeaseLost(RuntimeError):
    pass


class SQLiteUploadLeases:
    def __init__(self, database: str | Path, *, lease_seconds: float = 60.0):
        if not isinstance(lease_seconds, (int, float)) or not 0 < lease_seconds < float("inf"):
            raise ValueError("lease_seconds must be positive")
        self.database = str(database)
        self.lease_seconds = lease_seconds
        with sqlite3.connect(self.database) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS upload_file_leases (
                lock_key TEXT PRIMARY KEY, token TEXT NOT NULL, expires_at REAL NOT NULL)""")

    @staticmethod
    def _key(customer_id: str, project_id: str, filename: str) -> str:
        from hashlib import sha256
        parts = (customer_id, project_id, filename)
        if any(not isinstance(p, str) or not p or p in (".", "..")
               or "/" in p or chr(92) in p or chr(0) in p for p in parts):
            raise ValueError("invalid lease identity")
        return sha256(chr(0).join(parts).encode("utf-8")).hexdigest()

    def acquire(self, customer_id: str, project_id: str, filename: str) -> tuple[str, str]:
        key = self._key(customer_id, project_id, filename)
        token = uuid4().hex
        now = time.time()
        with sqlite3.connect(self.database, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM upload_file_leases WHERE lock_key=? AND expires_at<=?", (key, now))
            cursor = db.execute("INSERT OR IGNORE INTO upload_file_leases VALUES (?, ?, ?)",
                                (key, token, now + self.lease_seconds))
            if cursor.rowcount != 1:
                raise UploadLeaseBusy("upload file is already leased")
        return key, token

    def renew(self, key: str, token: str) -> bool:
        with sqlite3.connect(self.database) as db:
            cursor = db.execute(
                "UPDATE upload_file_leases SET expires_at=? WHERE lock_key=? AND token=? AND expires_at>?",
                (time.time() + self.lease_seconds, key, token, time.time()))
            return cursor.rowcount == 1

    def release(self, key: str, token: str) -> bool:
        with sqlite3.connect(self.database) as db:
            cursor = db.execute("DELETE FROM upload_file_leases WHERE lock_key=? AND token=?", (key, token))
            return cursor.rowcount == 1

    @contextmanager
    def hold(self, customer_id: str, project_id: str, filename: str):
        key, token = self.acquire(customer_id, project_id, filename)
        stopped = threading.Event()
        lost = threading.Event()

        def heartbeat():
            while not stopped.wait(self.lease_seconds / 3):
                try:
                    if not self.renew(key, token):
                        lost.set()
                        return
                except sqlite3.Error:
                    lost.set()
                    return

        worker = threading.Thread(target=heartbeat, daemon=True)
        worker.start()
        try:
            yield
            try:
                owned = self.renew(key, token)
            except sqlite3.Error as exc:
                raise UploadLeaseLost("unable to confirm upload lease ownership") from exc
            if lost.is_set() or not owned:
                raise UploadLeaseLost("upload coordination lease was lost")
        finally:
            stopped.set()
            worker.join()
            self.release(key, token)
