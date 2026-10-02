"""SQLite persistence for versioned SolarCheck evaluation tariffs."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from mcm_solarcheck.services.payment import PaymentAmount
from mcm_solarcheck.services.solarcheck_tariff import (
    SolarCheckPriceBand,
    SolarCheckTariff,
)


class SQLiteSolarCheckTariffStore:
    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS solarcheck_tariffs (
                    version INTEGER PRIMARY KEY,
                    effective_from TEXT NOT NULL,
                    active INTEGER NOT NULL CHECK (active IN (0, 1))
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS solarcheck_tariff_bands (
                    tariff_version INTEGER NOT NULL,
                    position INTEGER NOT NULL,
                    min_kwp INTEGER NOT NULL,
                    max_kwp INTEGER NOT NULL,
                    amount_minor_units INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    PRIMARY KEY (tariff_version, position),
                    FOREIGN KEY (tariff_version)
                        REFERENCES solarcheck_tariffs(version)
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def save(self, tariff: SolarCheckTariff) -> None:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO solarcheck_tariffs(version, effective_from, active)
                VALUES (?, ?, ?)
                """,
                (tariff.version, tariff.effective_from.isoformat(), int(tariff.active)),
            )
            connection.executemany(
                """
                INSERT INTO solarcheck_tariff_bands(
                    tariff_version, position, min_kwp, max_kwp,
                    amount_minor_units, currency
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        tariff.version,
                        position,
                        band.min_kwp,
                        band.max_kwp,
                        band.amount.minor_units,
                        band.amount.currency,
                    )
                    for position, band in enumerate(tariff.bands)
                ],
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def is_configured(self) -> bool:
        """Return whether an active tariff is effective for current UTC time."""
        from datetime import timezone

        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM solarcheck_tariffs
                WHERE active = 1 AND effective_from <= ?
                LIMIT 1
                """,
                (now,),
            ).fetchone()
        return row is not None

    def current(self, at: datetime) -> SolarCheckTariff:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT version, effective_from, active
                FROM solarcheck_tariffs
                WHERE active = 1 AND effective_from <= ?
                ORDER BY effective_from DESC, version DESC
                LIMIT 1
                """,
                (at.isoformat(),),
            ).fetchone()
            if row is None:
                raise ValueError("no active SolarCheck tariff is effective")
            bands = connection.execute(
                """
                SELECT min_kwp, max_kwp, amount_minor_units, currency
                FROM solarcheck_tariff_bands
                WHERE tariff_version = ?
                ORDER BY position
                """,
                (row[0],),
            ).fetchall()
        return SolarCheckTariff(
            row[0],
            tuple(
                SolarCheckPriceBand(
                    band[0],
                    band[1],
                    PaymentAmount(band[2], band[3]),
                )
                for band in bands
            ),
            datetime.fromisoformat(row[1]),
            bool(row[2]),
        )
