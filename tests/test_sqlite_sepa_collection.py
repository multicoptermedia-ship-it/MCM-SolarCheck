import sqlite3

import pytest

from mcm_solarcheck.infrastructure.sqlite_sepa_collection import (
    SQLiteSepaCollectionStore,
)
from mcm_solarcheck.services.sepa_collection import (
    SepaCollection,
    SepaCollectionStatus,
)


def collection(collection_id: str = "collection-a") -> SepaCollection:
    return SepaCollection(
        collection_id,
        "payment-a",
        "user-a",
        "project-a",
        "provider-a",
        "provider-debit-a",
    )


def test_sepa_collection_persists_async_transitions(tmp_path) -> None:
    database = tmp_path / "collections.sqlite"
    store = SQLiteSepaCollectionStore(database)
    store.create(collection())

    pending = store.transition(
        "collection-a",
        user_id="user-a",
        target=SepaCollectionStatus.PENDING,
    )
    assert pending.status is SepaCollectionStatus.PENDING

    succeeded = store.transition(
        "collection-a",
        user_id="user-a",
        target=SepaCollectionStatus.SUCCEEDED,
    )
    assert SQLiteSepaCollectionStore(database).get(
        "collection-a"
    ) == succeeded


def test_only_one_sepa_collection_is_allowed_per_payment(tmp_path) -> None:
    store = SQLiteSepaCollectionStore(tmp_path / "collections.sqlite")
    store.create(collection())

    with pytest.raises(sqlite3.IntegrityError):
        store.create(collection("collection-b"))


def test_sepa_collection_transition_is_owner_guarded(tmp_path) -> None:
    store = SQLiteSepaCollectionStore(tmp_path / "collections.sqlite")
    store.create(collection())

    with pytest.raises(PermissionError, match="ownership"):
        store.transition(
            "collection-a",
            user_id="user-b",
            target=SepaCollectionStatus.SUCCEEDED,
        )


def test_sepa_provider_reference_is_unique_per_provider(tmp_path) -> None:
    store = SQLiteSepaCollectionStore(tmp_path / "collections.sqlite")
    store.create(
        SepaCollection(
            "collection-a", "payment-a", "user-a", "project-a",
            "provider-a", "provider-ref-a",
        )
    )

    with pytest.raises(sqlite3.IntegrityError):
        store.create(
            SepaCollection(
                "collection-b", "payment-b", "user-b", "project-b",
                "provider-a", "provider-ref-a",
            )
        )


def test_legacy_duplicate_sepa_provider_reference_blocks_migration(tmp_path) -> None:
    database = tmp_path / "collections.sqlite"
    connection = sqlite3.connect(database)
    connection.execute(
        """
        CREATE TABLE sepa_collections (
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
    for suffix in ("a", "b"):
        connection.execute(
            """
            INSERT INTO sepa_collections (
                collection_id, payment_id, user_id, project_id,
                provider_id, provider_reference, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"collection-{suffix}",
                f"payment-{suffix}",
                f"user-{suffix}",
                f"project-{suffix}",
                "provider-a",
                "provider-ref-duplicate",
                SepaCollectionStatus.SUBMITTED.value,
            ),
        )
    connection.commit()
    connection.close()

    with pytest.raises(ValueError, match="duplicate provider reference"):
        SQLiteSepaCollectionStore(database)
