"""SQLite persistence for asynchronous SEPA collections."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from mcm_solarcheck.services.sepa_collection import (
    SepaCollection,
    SepaCollectionStatus,
)


class SQLiteSepaCollectionStore:
    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sepa_collections (
                    collection_id TEXT PRIMARY KEY,
                    payment_id TEXT NOT NULL UNIQUE,
                    user_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    provider_id TEXT NOT NULL,
                    provider_reference TEXT NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database)

    def create(self, collection: SepaCollection) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sepa_collections (
                    collection_id, payment_id, user_id, project_id,
                    provider_id, provider_reference, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    collection.collection_id,
                    collection.payment_id,
                    collection.user_id,
                    collection.project_id,
                    collection.provider_id,
                    collection.provider_reference,
                    collection.status.value,
                ),
            )

    def get(self, collection_id: str) -> SepaCollection:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payment_id, user_id, project_id, provider_id,
                       provider_reference, status
                FROM sepa_collections
                WHERE collection_id = ?
                """,
                (collection_id,),
            ).fetchone()
        if row is None:
            raise KeyError(collection_id)
        return SepaCollection(
            collection_id,
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            SepaCollectionStatus(row[5]),
        )

    def transition(
        self,
        collection_id: str,
        *,
        user_id: str,
        target: SepaCollectionStatus,
    ) -> SepaCollection:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT payment_id, user_id, project_id, provider_id,
                       provider_reference, status
                FROM sepa_collections
                WHERE collection_id = ?
                """,
                (collection_id,),
            ).fetchone()
            if row is None:
                raise KeyError(collection_id)
            if row[1] != user_id:
                raise PermissionError("SEPA collection ownership mismatch")

            current = SepaCollection(
                collection_id,
                row[0],
                row[1],
                row[2],
                row[3],
                row[4],
                SepaCollectionStatus(row[5]),
            )
            transitions = {
                SepaCollectionStatus.PENDING: current.pending,
                SepaCollectionStatus.SUCCEEDED: current.succeed,
                SepaCollectionStatus.FAILED: current.fail,
                SepaCollectionStatus.RETURNED: current.returned,
            }
            try:
                updated = transitions[target]()
            except KeyError:
                raise ValueError("unsupported SEPA collection transition") from None

            connection.execute(
                """
                UPDATE sepa_collections
                SET status = ?
                WHERE collection_id = ?
                """,
                (updated.status.value, collection_id),
            )
            connection.commit()
            return updated
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
