from __future__ import annotations

import sqlite3

from mcm_solarcheck.infrastructure.sqlite_sepa_collection import SQLiteSepaCollectionStore


def test_sepa_collection_storage_schema_stays_minimal(tmp_path) -> None:
    database = tmp_path / "collections-schema.sqlite"
    SQLiteSepaCollectionStore(database)

    with sqlite3.connect(database) as connection:
        columns = [
            row[1]
            for row in connection.execute("PRAGMA table_info(sepa_collections)")
        ]

    assert columns == [
        "collection_id",
        "payment_id",
        "user_id",
        "project_id",
        "provider_id",
        "provider_reference",
        "status",
    ]
