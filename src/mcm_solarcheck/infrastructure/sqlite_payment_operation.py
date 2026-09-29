"""SQLite reservation for mutually exclusive payment terminal operations."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from mcm_solarcheck.services.payment_operation import (
    PaymentOperation,
    PaymentOperationIntent,
)


class SQLitePaymentOperationIntentStore:
    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS payment_operation_intents (
                    payment_id TEXT PRIMARY KEY,
                    operation TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database, timeout=30)

    def reserve(self, intent: PaymentOperationIntent) -> PaymentOperationIntent:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT operation
                FROM payment_operation_intents
                WHERE payment_id = ?
                """,
                (intent.payment_id,),
            ).fetchone()
            if row is not None:
                existing = PaymentOperationIntent(
                    intent.payment_id,
                    PaymentOperation(row[0]),
                )
                if existing.operation is not intent.operation:
                    raise ValueError(
                        "conflicting terminal payment operation already reserved"
                    )
                connection.commit()
                return existing

            connection.execute(
                """
                INSERT INTO payment_operation_intents (payment_id, operation)
                VALUES (?, ?)
                """,
                (intent.payment_id, intent.operation.value),
            )
            connection.commit()
            return intent
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
