"""SQLite persistence for versioned merchant payment accounts."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from mcm_solarcheck.services.merchant_account import (
    MerchantAccount,
    MerchantAccountKind,
)


class SQLiteMerchantAccountStore:
    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS merchant_accounts (
                    account_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    provider_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    display_reference TEXT NOT NULL,
                    active INTEGER NOT NULL,
                    credential_key TEXT,
                    PRIMARY KEY (account_id, version)
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database)

    def save(self, account: MerchantAccount) -> None:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            latest = connection.execute(
                """
                SELECT version, provider_id, kind
                FROM merchant_accounts
                WHERE account_id = ?
                ORDER BY version DESC
                LIMIT 1
                """,
                (account.account_id,),
            ).fetchone()
            expected = 1 if latest is None else latest[0] + 1
            if account.version != expected:
                raise ValueError("merchant account version is not next")
            if latest is not None:
                if account.provider_id != latest[1]:
                    raise ValueError(
                        "merchant account provider cannot change across versions"
                    )
                if account.kind.value != latest[2]:
                    raise ValueError(
                        "merchant account kind cannot change across versions"
                    )

            connection.execute(
                """
                INSERT INTO merchant_accounts (
                    account_id, version, provider_id, kind,
                    display_reference, active, credential_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    account.account_id,
                    account.version,
                    account.provider_id,
                    account.kind.value,
                    account.display_reference,
                    int(account.active),
                    account.credential_key,
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get(self, account_id: str, version: int) -> MerchantAccount:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT provider_id, kind, display_reference,
                       active, credential_key
                FROM merchant_accounts
                WHERE account_id = ? AND version = ?
                """,
                (account_id, version),
            ).fetchone()
        if row is None:
            raise KeyError((account_id, version))
        return MerchantAccount(
            account_id,
            row[0],
            MerchantAccountKind(row[1]),
            row[2],
            version,
            bool(row[3]),
            row[4],
        )

    def is_configured(self) -> bool:
        """Require active current accounts for card, PayPal and SEPA operation."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT m.kind, m.active
                FROM merchant_accounts AS m
                JOIN (
                    SELECT account_id, MAX(version) AS version
                    FROM merchant_accounts
                    GROUP BY account_id
                ) AS latest
                  ON latest.account_id = m.account_id
                 AND latest.version = m.version
                """
            ).fetchall()
        active_kinds = {kind for kind, active in rows if bool(active)}
        return active_kinds == {kind.value for kind in MerchantAccountKind}

    def current(self, account_id: str) -> MerchantAccount:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT version, provider_id, kind, display_reference,
                       active, credential_key
                FROM merchant_accounts
                WHERE account_id = ?
                ORDER BY version DESC
                LIMIT 1
                """,
                (account_id,),
            ).fetchone()
        if row is None:
            raise KeyError(account_id)
        account = MerchantAccount(
            account_id,
            row[1],
            MerchantAccountKind(row[2]),
            row[3],
            row[0],
            bool(row[4]),
            row[5],
        )
        if not account.active:
            raise ValueError("merchant account is inactive")
        return account
