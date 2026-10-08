"""SQLite persistence for active online product entitlements."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from mcm_solarcheck.services.online_entitlement import OnlineEntitlement, OnlineProduct


class SQLiteOnlineEntitlementStore:
    """Persist the authoritative active product entitlement per online user."""

    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS online_entitlements (
                    user_id TEXT PRIMARY KEY,
                    product TEXT NOT NULL,
                    active INTEGER NOT NULL CHECK (active IN (0, 1))
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database)

    def save(self, entitlement: OnlineEntitlement) -> None:
        if not entitlement.active:
            raise ValueError("only active online entitlements may be persisted")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO online_entitlements (user_id, product, active)
                VALUES (?, ?, 1)
                ON CONFLICT(user_id) DO UPDATE SET
                    product = excluded.product,
                    active = excluded.active
                """,
                (entitlement.user_id, entitlement.product.value),
            )

    def get(self, user_id: str) -> OnlineEntitlement:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT product, active FROM online_entitlements WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if row is None:
            raise KeyError(user_id)
        return OnlineEntitlement(user_id, OnlineProduct(row[0]), bool(row[1]))

    def require_active(self, user_id: str) -> OnlineEntitlement:
        try:
            entitlement = self.get(user_id)
        except KeyError as exc:
            raise PermissionError("active online product entitlement required") from exc
        if not entitlement.active:
            raise PermissionError("active online product entitlement required")
        return entitlement
