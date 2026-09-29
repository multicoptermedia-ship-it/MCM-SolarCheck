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
