"""SQLite persistence for admin-configured FlightPlan vouchers."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from mcm_solarcheck.services.payment import PaymentAmount
from mcm_solarcheck.services.voucher import FlightPlanVoucher


class SQLiteFlightPlanVoucherStore:
    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS flightplan_vouchers (
                    code TEXT PRIMARY KEY,
                    value_minor_units INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    valid_from TEXT NOT NULL,
                    valid_until TEXT NOT NULL,
                    redeemed_payment_id TEXT,
                    redeemed_at TEXT
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database)

    def create(self, voucher: FlightPlanVoucher) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO flightplan_vouchers (
                    code, value_minor_units, currency, valid_from, valid_until,
                    redeemed_payment_id, redeemed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    voucher.code,
                    voucher.value.minor_units,
                    voucher.value.currency,
                    voucher.valid_from.isoformat(),
                    voucher.valid_until.isoformat(),
                    voucher.redeemed_payment_id,
                    voucher.redeemed_at.isoformat() if voucher.redeemed_at else None,
                ),
            )

    def get(self, code: str) -> FlightPlanVoucher:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT value_minor_units, currency, valid_from, valid_until,
                       redeemed_payment_id, redeemed_at
                FROM flightplan_vouchers
                WHERE code = ?
                """,
                (code.strip(),),
            ).fetchone()
        if row is None:
            raise KeyError(code)
        return self._from_row(code.strip(), row)

    def redeem(
        self, code: str, payment_id: str, *, now: datetime
    ) -> FlightPlanVoucher:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            normalized = code.strip()
            row = connection.execute(
                """
                SELECT value_minor_units, currency, valid_from, valid_until,
                       redeemed_payment_id, redeemed_at
                FROM flightplan_vouchers
                WHERE code = ?
                """,
                (normalized,),
            ).fetchone()
            if row is None:
                raise KeyError(code)
            current = self._from_row(normalized, row)
            redeemed = current.redeem(payment_id, now=now)
            connection.execute(
                """
                UPDATE flightplan_vouchers
                SET redeemed_payment_id = ?, redeemed_at = ?
                WHERE code = ?
                """,
                (
                    redeemed.redeemed_payment_id,
                    redeemed.redeemed_at.isoformat(),
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
            PaymentAmount(row[0], row[1]),
            datetime.fromisoformat(row[2]),
            datetime.fromisoformat(row[3]),
            row[4],
            datetime.fromisoformat(row[5]) if row[5] is not None else None,
        )
