"""SQLite persistence for FlightPlan voucher redemption."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from mcm_solarcheck.services.voucher import FlightPlanVoucher
from mcm_solarcheck.services.voucher_admin import FlightPlanVoucherPolicy


class SQLiteFlightPlanVoucherStore:
    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS flightplan_vouchers (
                    code TEXT PRIMARY KEY,
                    valid_from TEXT NOT NULL,
                    valid_until TEXT NOT NULL,
                    redeemed_payment_id TEXT,
                    redeemed_at TEXT,
                    redeemed_discount_percent INTEGER,
                    redeemed_policy_version INTEGER
                )
                """
            )
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(flightplan_vouchers)")
            }
            if "redeemed_policy_version" not in columns:
                connection.execute(
                    "ALTER TABLE flightplan_vouchers "
                    "ADD COLUMN redeemed_policy_version INTEGER"
                )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database)

    def create(self, voucher: FlightPlanVoucher) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO flightplan_vouchers (
                    code, valid_from, valid_until, redeemed_payment_id,
                    redeemed_at, redeemed_discount_percent,
                    redeemed_policy_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    voucher.code,
                    voucher.valid_from.isoformat(),
                    voucher.valid_until.isoformat(),
                    voucher.redeemed_payment_id,
                    voucher.redeemed_at.isoformat() if voucher.redeemed_at else None,
                    voucher.redeemed_discount_percent,
                    voucher.redeemed_policy_version,
                ),
            )

    def get(self, code: str) -> FlightPlanVoucher:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT valid_from, valid_until, redeemed_payment_id,
                       redeemed_at, redeemed_discount_percent,
                       redeemed_policy_version
                FROM flightplan_vouchers WHERE code = ?
                """,
                (code.strip(),),
            ).fetchone()
        if row is None:
            raise KeyError(code)
        return self._from_row(code.strip(), row)

    def redeem(
        self,
        code: str,
        payment_id: str,
        *,
        discount_percent: int,
        policy_version: int | None = None,
        now: datetime,
    ) -> FlightPlanVoucher:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            normalized = code.strip()
            row = connection.execute(
                """
                SELECT valid_from, valid_until, redeemed_payment_id,
                       redeemed_at, redeemed_discount_percent,
                       redeemed_policy_version
                FROM flightplan_vouchers WHERE code = ?
                """,
                (normalized,),
            ).fetchone()
            if row is None:
                raise KeyError(code)
            current = self._from_row(normalized, row)
            redeemed = current.redeem(
                payment_id,
                discount_percent=discount_percent,
                now=now,
                policy_version=policy_version,
            )
            connection.execute(
                """
                UPDATE flightplan_vouchers
                SET redeemed_payment_id = ?, redeemed_at = ?,
                    redeemed_discount_percent = ?,
                    redeemed_policy_version = ?
                WHERE code = ?
                """,
                (
                    redeemed.redeemed_payment_id,
                    redeemed.redeemed_at.isoformat(),
                    redeemed.redeemed_discount_percent,
                    redeemed.redeemed_policy_version,
                    normalized,
                ),
            )
            connection.commit()
            return redeemed
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _from_row(code: str, row) -> FlightPlanVoucher:
        return FlightPlanVoucher(
            code,
            datetime.fromisoformat(row[0]),
            datetime.fromisoformat(row[1]),
            row[2],
            datetime.fromisoformat(row[3]) if row[3] is not None else None,
            row[4],
            row[5],
        )


class SQLiteFlightPlanVoucherPolicyStore:
    """Append-only history for the global FlightPlan discount policy."""

    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS flightplan_voucher_policy (
                    version INTEGER PRIMARY KEY,
                    discount_percent INTEGER NOT NULL,
                    active INTEGER NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database, timeout=30)

    def bootstrap_default(self) -> FlightPlanVoucherPolicy:
        """Create the initial 10% policy exactly once for legacy databases."""
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT version, discount_percent, active
                FROM flightplan_voucher_policy
                ORDER BY version DESC
                LIMIT 1
                """
            ).fetchone()
            if row is not None:
                connection.commit()
                return FlightPlanVoucherPolicy(row[1], row[0], bool(row[2]))
            policy = FlightPlanVoucherPolicy()
            connection.execute(
                """
                INSERT INTO flightplan_voucher_policy (
                    version, discount_percent, active
                ) VALUES (?, ?, ?)
                """,
                (policy.version, policy.discount_percent, int(policy.active)),
            )
            connection.commit()
            return policy
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def save(self, policy: FlightPlanVoucherPolicy) -> None:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT version
                FROM flightplan_voucher_policy
                ORDER BY version DESC
                LIMIT 1
                """
            ).fetchone()
            expected = 1 if row is None else row[0] + 1
            if policy.version != expected:
                raise ValueError("voucher policy version is not next")
            connection.execute(
                """
                INSERT INTO flightplan_voucher_policy (
                    version, discount_percent, active
                ) VALUES (?, ?, ?)
                """,
                (
                    policy.version,
                    policy.discount_percent,
                    int(policy.active),
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get(self, version: int) -> FlightPlanVoucherPolicy:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT discount_percent, active
                FROM flightplan_voucher_policy
                WHERE version = ?
                """,
                (version,),
            ).fetchone()
        if row is None:
            raise KeyError(version)
        return FlightPlanVoucherPolicy(row[0], version, bool(row[1]))

    def current(self) -> FlightPlanVoucherPolicy:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT version, discount_percent, active
                FROM flightplan_voucher_policy
                ORDER BY version DESC
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            raise KeyError("voucher policy is not configured")
        policy = FlightPlanVoucherPolicy(row[1], row[0], bool(row[2]))
        if not policy.active:
            raise ValueError("voucher policy is inactive")
        return policy
