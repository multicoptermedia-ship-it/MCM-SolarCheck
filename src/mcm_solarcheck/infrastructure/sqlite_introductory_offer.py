"""SQLite usage evidence for the one-time SolarCheck introductory offer."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


class SQLiteIntroductoryOfferStore:
    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS introductory_offer_usage (
                    user_id TEXT PRIMARY KEY,
                    payment_id TEXT NOT NULL UNIQUE,
                    policy_version INTEGER NOT NULL,
                    used_at TEXT NOT NULL
                )
                """
            )

    def has_used(self, user_id: str) -> bool:
        with sqlite3.connect(self.database) as connection:
            row = connection.execute(
                "SELECT 1 FROM introductory_offer_usage WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return row is not None

    def mark_used(
        self,
        user_id: str,
        payment_id: str,
        *,
        policy_version: int,
        used_at: datetime,
    ) -> None:
        if not user_id.strip() or not payment_id.strip():
            raise ValueError("offer usage identity must be non-empty")
        if policy_version <= 0:
            raise ValueError("policy_version must be positive")
        if used_at.tzinfo is None or used_at.utcoffset() is None:
            raise ValueError("used_at must be timezone-aware")
        with sqlite3.connect(self.database) as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO introductory_offer_usage(
                        user_id, payment_id, policy_version, used_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (user_id.strip(), payment_id.strip(), policy_version, used_at.isoformat()),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("introductory offer already used") from exc
