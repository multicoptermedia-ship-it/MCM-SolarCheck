"""SQLite persistence for payment authorization crash recovery."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from mcm_solarcheck.services.payment_authorization_intent import (
    PaymentAuthorizationIntent,
    PaymentAuthorizationIntentStatus,
)


class SQLitePaymentAuthorizationIntentStore:
    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with sqlite3.connect(self.database, timeout=30) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS payment_authorization_intents (
                    payment_id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL,
                    status TEXT NOT NULL,
                    provider_reference TEXT
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database, timeout=30)

    @staticmethod
    def _from_row(payment_id: str, row) -> PaymentAuthorizationIntent:
        return PaymentAuthorizationIntent(
            payment_id,
            row[0],
            PaymentAuthorizationIntentStatus(row[1]),
            row[2],
        )

    def get(self, payment_id: str) -> PaymentAuthorizationIntent:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT idempotency_key, status, provider_reference
                   FROM payment_authorization_intents WHERE payment_id = ?""",
                (payment_id,),
            ).fetchone()
        if row is None:
            raise KeyError(payment_id)
        return self._from_row(payment_id, row)

    def reserve(self, intent: PaymentAuthorizationIntent) -> PaymentAuthorizationIntent:
        if intent.status is not PaymentAuthorizationIntentStatus.RESERVED:
            raise ValueError("new authorization intent must be reserved")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """SELECT idempotency_key, status, provider_reference
                   FROM payment_authorization_intents WHERE payment_id = ?""",
                (intent.payment_id,),
            ).fetchone()
            if row is not None:
                existing = self._from_row(intent.payment_id, row)
                if existing.idempotency_key != intent.idempotency_key:
                    raise ValueError("conflicting authorization idempotency key")
                connection.commit()
                return existing
            connection.execute(
                """INSERT INTO payment_authorization_intents
                   (payment_id, idempotency_key, status, provider_reference)
                   VALUES (?, ?, ?, NULL)""",
                (intent.payment_id, intent.idempotency_key, intent.status.value),
            )
            connection.commit()
            return intent
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def mark_provider_succeeded(
        self, payment_id: str, provider_reference: str
    ) -> PaymentAuthorizationIntent:
        if not isinstance(provider_reference, str) or not provider_reference.strip():
            raise ValueError("provider_reference must be non-empty")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """SELECT idempotency_key, status, provider_reference
                   FROM payment_authorization_intents WHERE payment_id = ?""",
                (payment_id,),
            ).fetchone()
            if row is None:
                raise KeyError(payment_id)
            current = self._from_row(payment_id, row)
            if current.status is not PaymentAuthorizationIntentStatus.RESERVED:
                if current.provider_reference != provider_reference:
                    raise ValueError("authorization provider reference mismatch")
                connection.commit()
                return current
            connection.execute(
                """UPDATE payment_authorization_intents
                   SET status = ?, provider_reference = ? WHERE payment_id = ?""",
                (
                    PaymentAuthorizationIntentStatus.PROVIDER_SUCCEEDED.value,
                    provider_reference.strip(),
                    payment_id,
                ),
            )
            connection.commit()
            return PaymentAuthorizationIntent(
                payment_id,
                current.idempotency_key,
                PaymentAuthorizationIntentStatus.PROVIDER_SUCCEEDED,
                provider_reference.strip(),
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def mark_completed(self, payment_id: str) -> PaymentAuthorizationIntent:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """SELECT idempotency_key, status, provider_reference
                   FROM payment_authorization_intents WHERE payment_id = ?""",
                (payment_id,),
            ).fetchone()
            if row is None:
                raise KeyError(payment_id)
            current = self._from_row(payment_id, row)
            if current.status is PaymentAuthorizationIntentStatus.COMPLETED:
                connection.commit()
                return current
            if current.status is not PaymentAuthorizationIntentStatus.PROVIDER_SUCCEEDED:
                raise ValueError("provider success required before completion")
            connection.execute(
                "UPDATE payment_authorization_intents SET status = ? WHERE payment_id = ?",
                (PaymentAuthorizationIntentStatus.COMPLETED.value, payment_id),
            )
            connection.commit()
            return PaymentAuthorizationIntent(
                payment_id,
                current.idempotency_key,
                PaymentAuthorizationIntentStatus.COMPLETED,
                current.provider_reference,
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
