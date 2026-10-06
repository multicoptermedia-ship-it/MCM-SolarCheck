"""Atomic SQLite persistence for voucher-priced payments."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from mcm_solarcheck.services.payment import OnlinePayment
from mcm_solarcheck.services.voucher import FlightPlanVoucher


class SQLitePricedPaymentStore:
    """Commit a payment and one-time voucher redemption in one transaction."""

    def __init__(self, payment_database: str | Path, voucher_database: str | Path) -> None:
        self.payment_database = str(payment_database)
        self.voucher_database = str(voucher_database)
        self._validate_schema()

    def _validate_schema(self) -> None:
        connection = sqlite3.connect(self.payment_database, timeout=30)
        try:
            same_database = Path(self.payment_database).resolve() == Path(self.voucher_database).resolve()
            if not same_database:
                connection.execute("ATTACH DATABASE ? AS vouchers", (self.voucher_database,))
            voucher_schema = "main" if same_database else "vouchers"
            payment_table = connection.execute(
                """
                SELECT 1 FROM main.sqlite_master
                WHERE type = 'table' AND name = 'online_payments'
                """
            ).fetchone()
            voucher_table = connection.execute(
                f"""
                SELECT 1 FROM {voucher_schema}.sqlite_master
                WHERE type = 'table' AND name = 'flightplan_vouchers'
                """
            ).fetchone()
            if payment_table is None:
                raise ValueError("payment database schema is not initialized")
            if voucher_table is None:
                raise ValueError("voucher database schema is not initialized")
            payment_journal = connection.execute(
                "PRAGMA main.journal_mode"
            ).fetchone()[0].lower()
            voucher_journal = connection.execute(
                f"PRAGMA {voucher_schema}.journal_mode"
            ).fetchone()[0].lower()
            if "wal" in {payment_journal, voucher_journal}:
                raise ValueError(
                    "atomic voucher payment persistence does not support WAL "
                    "across attached databases"
                )
        finally:
            connection.close()

    def create_with_voucher(
        self,
        payment: OnlinePayment,
        *,
        voucher_code: str,
        discount_percent: int,
        policy_version: int,
        now: datetime,
    ) -> FlightPlanVoucher:
        connection = sqlite3.connect(self.payment_database, timeout=30)
        try:
            same_database = Path(self.payment_database).resolve() == Path(self.voucher_database).resolve()
            if not same_database:
                connection.execute("ATTACH DATABASE ? AS vouchers", (self.voucher_database,))
            voucher_schema = "main" if same_database else "vouchers"
            connection.execute("BEGIN IMMEDIATE")
            normalized = voucher_code.strip()
            row = connection.execute(
                f"""
                SELECT valid_from, valid_until, redeemed_payment_id,
                       redeemed_at, redeemed_discount_percent,
                       redeemed_policy_version
                FROM {voucher_schema}.flightplan_vouchers
                WHERE code = ?
                """,
                (normalized,),
            ).fetchone()
            if row is None:
                raise KeyError(voucher_code)
            current = FlightPlanVoucher(
                normalized,
                datetime.fromisoformat(row[0]),
                datetime.fromisoformat(row[1]),
                row[2],
                datetime.fromisoformat(row[3]) if row[3] is not None else None,
                row[4],
                row[5],
            )
            redeemed = current.redeem(
                payment.payment_id,
                discount_percent=discount_percent,
                now=now,
                policy_version=policy_version,
            )
            existing_job = connection.execute(
                """
                SELECT payment_id
                FROM online_payments
                WHERE job_id = ?
                """,
                (payment.job_id,),
            ).fetchone()
            if existing_job is not None:
                raise ValueError("compute job already has a payment")
            connection.execute(
                """
                INSERT INTO online_payments (
                    payment_id, user_id, project_id, job_id,
                    amount_minor_units, currency, status, provider_reference, method,
                    merchant_account_id, merchant_account_version, provider_id,
                    tariff_version, plant_kwp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payment.payment_id,
                    payment.user_id,
                    payment.project_id,
                    payment.job_id,
                    payment.amount.minor_units if payment.amount else None,
                    payment.amount.currency if payment.amount else None,
                    payment.status.value,
                    payment.provider_reference,
                    payment.method.value if payment.method else None,
                    payment.merchant_account_id,
                    payment.merchant_account_version,
                    payment.provider_id,
                    payment.tariff_version,
                    payment.plant_kwp,
                ),
            )
            connection.execute(
                f"""
                UPDATE {voucher_schema}.flightplan_vouchers
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
