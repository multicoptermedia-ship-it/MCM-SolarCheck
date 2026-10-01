from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.sqlite_sepa_collection import SQLiteSepaCollectionStore
from mcm_solarcheck.services.sepa_collection import SepaCollection, SepaCollectionStatus
from mcm_solarcheck.services.sepa_collection_update import SepaCollectionUpdateService


def setup_collection(tmp_path):
    store = SQLiteSepaCollectionStore(tmp_path / "collections.sqlite")
    store.create(
        SepaCollection(
            "collection-a",
            "payment-a",
            "user-a",
            "project-a",
            "provider-a",
            "provider-debit-a",
        )
    )
    return store, SepaCollectionUpdateService(store)


def test_verified_provider_updates_collection_by_provider_reference(tmp_path) -> None:
    store, service = setup_collection(tmp_path)

    pending = service.apply_verified_update(
        "provider-a", "provider-debit-a", SepaCollectionStatus.PENDING
    )
    succeeded = service.apply_verified_update(
        "provider-a", "provider-debit-a", SepaCollectionStatus.SUCCEEDED
    )
    returned = service.apply_verified_update(
        "provider-a", "provider-debit-a", SepaCollectionStatus.RETURNED
    )

    assert pending.status is SepaCollectionStatus.PENDING
    assert succeeded.status is SepaCollectionStatus.SUCCEEDED
    assert returned.status is SepaCollectionStatus.RETURNED
    assert store.get("collection-a") == returned


def test_provider_update_cannot_target_wrong_provider_or_reference(tmp_path) -> None:
    store, service = setup_collection(tmp_path)

    with pytest.raises(KeyError):
        service.apply_verified_update(
            "provider-b", "provider-debit-a", SepaCollectionStatus.SUCCEEDED
        )
    with pytest.raises(KeyError):
        service.apply_verified_update(
            "provider-a", "provider-debit-b", SepaCollectionStatus.SUCCEEDED
        )

    assert store.get("collection-a").status is SepaCollectionStatus.SUBMITTED


def test_failed_or_returned_collection_cannot_be_reopened(tmp_path) -> None:
    store, service = setup_collection(tmp_path)
    service.apply_verified_update(
        "provider-a", "provider-debit-a", SepaCollectionStatus.FAILED
    )

    with pytest.raises(ValueError, match="cannot transition"):
        service.apply_verified_update(
            "provider-a", "provider-debit-a", SepaCollectionStatus.SUCCEEDED
        )
    assert store.get("collection-a").status is SepaCollectionStatus.FAILED

    other = SepaCollection(
        "collection-b",
        "payment-b",
        "user-a",
        "project-a",
        "provider-a",
        "provider-debit-b",
    )
    store.create(other)
    service.apply_verified_update(
        "provider-a", "provider-debit-b", SepaCollectionStatus.SUCCEEDED
    )
    service.apply_verified_update(
        "provider-a", "provider-debit-b", SepaCollectionStatus.RETURNED
    )
    with pytest.raises(ValueError, match="cannot transition"):
        service.apply_verified_update(
            "provider-a", "provider-debit-b", SepaCollectionStatus.SUCCEEDED
        )
    assert store.get("collection-b").status is SepaCollectionStatus.RETURNED
