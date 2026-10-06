"""SQLite reservation and usage evidence for the one-time SolarCheck offer."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from mcm_solarcheck.services.introductory_offer import (
    IntroductoryOfferReservationNotFound,
)


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
                    used_at TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'used'
                )
                """
            )
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(introductory_offer_usage)"
                )
            }
            if "state" not in columns:
                connection.execute(
                    "ALTER TABLE introductory_offer_usage "
                    "ADD COLUMN state TEXT NOT NULL DEFAULT 'used'"
                )

    def has_used(self, user_id: str) -> bool:
        with sqlite3.connect(self.database) as connection:
            row = connection.execute(
                """
                SELECT 1 FROM introductory_offer_usage
                WHERE user_id = ? AND state = 'used'
                """,
                (user_id,),
            ).fetchone()
        return row is not None

    def reserve(
        self,
        user_id: str,
        payment_id: str,
        *,
        policy_version: int,
        now: datetime,
    ) -> bool:
        self._validate(user_id, payment_id, policy_version, now)
        try:
            with sqlite3.connect(self.database) as connection:
                connection.execute(
                    """
                    INSERT INTO introductory_offer_usage(
                        user_id, payment_id, policy_version, used_at, state
                    ) VALUES (?, ?, ?, ?, 'reserved')
                    """,
                    (user_id.strip(), payment_id.strip(), policy_version, now.isoformat()),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def finalize(self, user_id: str, payment_id: str, *, used_at: datetime) -> None:
        if used_at.tzinfo is None or used_at.utcoffset() is None:
            raise ValueError("used_at must be timezone-aware")
        with sqlite3.connect(self.database) as connection:
            cursor = connection.execute(
                """
                UPDATE introductory_offer_usage
                SET state = 'used', used_at = ?
                WHERE user_id = ? AND payment_id = ? AND state = 'reserved'
                """,
                (used_at.isoformat(), user_id.strip(), payment_id.strip()),
            )
            if cursor.rowcount == 1:
                return
            row = connection.execute(
                """
                SELECT state FROM introductory_offer_usage
                WHERE user_id = ? AND payment_id = ?
                """,
                (user_id.strip(), payment_id.strip()),
            ).fetchone()
            if row is not None and row[0] == "used":
                return
            raise IntroductoryOfferReservationNotFound(
                "introductory offer reservation not found"
            )

    def release(self, user_id: str, payment_id: str) -> None:
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                """
                DELETE FROM introductory_offer_usage
                WHERE user_id = ? AND payment_id = ? AND state = 'reserved'
                """,
                (user_id.strip(), payment_id.strip()),
            )

    def mark_used(
        self,
        user_id: str,
        payment_id: str,
        *,
        policy_version: int,
        used_at: datetime,
    ) -> None:
        if not self.reserve(
            user_id,
            payment_id,
            policy_version=policy_version,
            now=used_at,
        ):
            raise ValueError("introductory offer already used")
        self.finalize(user_id, payment_id, used_at=used_at)

    @staticmethod
    def _validate(
        user_id: str,
        payment_id: str,
        policy_version: int,
        used_at: datetime,
    ) -> None:
        if not user_id.strip() or not payment_id.strip():
            raise ValueError("offer usage identity must be non-empty")
        if policy_version <= 0:
            raise ValueError("policy_version must be positive")
        if used_at.tzinfo is None or used_at.utcoffset() is None:
            raise ValueError("used_at must be timezone-aware")
