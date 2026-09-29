"""SQLite persistence for FlightPlan voucher redemption."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from mcm_solarcheck.services.voucher import FlightPlanVoucher


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
                    redeemed_discount_percent INTEGER
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
                    code, valid_from, valid_until, redeemed_payment_id,
                    redeemed_at, redeemed_discount_percent
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    voucher.code,
                    voucher.valid_from.isoformat(),
                    voucher.valid_until.isoformat(),
                    voucher.redeemed_payment_id,
                    voucher.redeemed_at.isoformat() if voucher.redeemed_at else None,
                    voucher.redeemed_discount_percent,
                ),
            )

    def get(self, code: str) -> FlightPlanVoucher:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT valid_from, valid_until, redeemed_payment_id,
                       redeemed_at, redeemed_discount_percent
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
        now: datetime,
    ) -> FlightPlanVoucher:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            normalized = code.strip()
            row = connection.execute(
                """
                SELECT valid_from, valid_until, redeemed_payment_id,
                       redeemed_at, redeemed_discount_percent
                FROM flightplan_vouchers WHERE code = ?
                """,
                (normalized,),
            ).fetchone()
            if row is None:
                raise KeyError(code)
            current = self._from_row(normalized, row)
            redeemed = current.redeem(
                payment_id, discount_percent=discount_percent, now=now
            )
            connection.execute(
                """
                UPDATE flightplan_vouchers
                SET redeemed_payment_id = ?, redeemed_at = ?,
                    redeemed_discount_percent = ?
                WHERE code = ?
                """,
                (
                    redeemed.redeemed_payment_id,
                    redeemed.redeemed_at.isoformat(),
                    redeemed.redeemed_discount_percent,
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
        )
