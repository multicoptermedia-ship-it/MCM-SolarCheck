"""SQLite lifecycle for mutually exclusive terminal payment operations."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from mcm_solarcheck.services.payment_operation import (
    PaymentOperation,
    PaymentOperationIntent,
    PaymentOperationStatus,
)


class SQLitePaymentOperationIntentStore:
    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS payment_operation_intents (
                    payment_id TEXT PRIMARY KEY,
                    operation TEXT NOT NULL,
                    idempotency_key TEXT,
                    status TEXT NOT NULL DEFAULT 'reserved'
                )
                """
            )
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(payment_operation_intents)"
                )
            }
            if "idempotency_key" not in columns:
                connection.execute(
                    "ALTER TABLE payment_operation_intents ADD COLUMN idempotency_key TEXT"
                )
            if "status" not in columns:
                connection.execute(
                    "ALTER TABLE payment_operation_intents "
                    "ADD COLUMN status TEXT NOT NULL DEFAULT 'reserved'"
                )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database, timeout=30)

    @staticmethod
    def _from_row(payment_id: str, row) -> PaymentOperationIntent:
        operation = PaymentOperation(row[0])
        key = row[1] or f"payment:{payment_id}:{operation.value}"
        return PaymentOperationIntent(
            payment_id,
            operation,
            key,
            PaymentOperationStatus(row[2]),
        )

    def get(self, payment_id: str) -> PaymentOperationIntent:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT operation, idempotency_key, status
                FROM payment_operation_intents
                WHERE payment_id = ?
                """,
                (payment_id,),
            ).fetchone()
        if row is None:
            raise KeyError(payment_id)
        return self._from_row(payment_id, row)

    def reserve(self, intent: PaymentOperationIntent) -> PaymentOperationIntent:
        if intent.status is not PaymentOperationStatus.RESERVED:
            raise ValueError("new payment operation intent must be reserved")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT operation, idempotency_key, status
                FROM payment_operation_intents
                WHERE payment_id = ?
                """,
                (intent.payment_id,),
            ).fetchone()
            if row is not None:
                existing = self._from_row(intent.payment_id, row)
                if existing.operation is not intent.operation:
                    raise ValueError(
                        "conflicting terminal payment operation already reserved"
                    )
                if existing.idempotency_key != intent.idempotency_key:
                    raise ValueError("conflicting payment operation idempotency key")
                connection.commit()
                return existing

            connection.execute(
                """
                INSERT INTO payment_operation_intents (
                    payment_id, operation, idempotency_key, status
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    intent.payment_id,
                    intent.operation.value,
                    intent.idempotency_key,
                    intent.status.value,
                ),
            )
            connection.commit()
            return intent
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _advance(
        self,
        payment_id: str,
        expected: PaymentOperationStatus,
        target: PaymentOperationStatus,
    ) -> PaymentOperationIntent:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT operation, idempotency_key, status
                FROM payment_operation_intents
                WHERE payment_id = ?
                """,
                (payment_id,),
            ).fetchone()
            if row is None:
                raise KeyError(payment_id)
            current = self._from_row(payment_id, row)
            if current.status is target:
                connection.commit()
                return current
            if current.status is not expected:
                raise ValueError("invalid payment operation status transition")
            connection.execute(
                """
                UPDATE payment_operation_intents
                SET status = ?
                WHERE payment_id = ?
                """,
                (target.value, payment_id),
            )
            connection.commit()
            return PaymentOperationIntent(
                current.payment_id,
                current.operation,
                current.idempotency_key,
                target,
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def mark_provider_succeeded(self, payment_id: str) -> PaymentOperationIntent:
        return self._advance(
            payment_id,
            PaymentOperationStatus.RESERVED,
            PaymentOperationStatus.PROVIDER_SUCCEEDED,
        )

    def mark_completed(self, payment_id: str) -> PaymentOperationIntent:
        return self._advance(
            payment_id,
            PaymentOperationStatus.PROVIDER_SUCCEEDED,
            PaymentOperationStatus.COMPLETED,
        )
