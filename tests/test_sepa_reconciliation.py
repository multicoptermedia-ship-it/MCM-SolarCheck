import pytest

from mcm_solarcheck.infrastructure.sqlite_sepa_collection import (
    SQLiteSepaCollectionStore,
)
from mcm_solarcheck.services.sepa_collection import (
    SepaCollection,
    SepaCollectionStatus,
)
from mcm_solarcheck.services.sepa_reconciliation import (
    SepaProviderEvent,
    SepaReconciliationService,
)


def store_with_collection(tmp_path) -> SQLiteSepaCollectionStore:
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
    return store


def test_provider_event_updates_matching_collection(tmp_path) -> None:
    store = store_with_collection(tmp_path)
    service = SepaReconciliationService(store)

    pending = service.apply(
        SepaProviderEvent(
            "provider-a",
            "provider-debit-a",
            SepaCollectionStatus.PENDING,
        )
    )
    assert pending.status is SepaCollectionStatus.PENDING

    succeeded = service.apply(
        SepaProviderEvent(
            "provider-a",
            "provider-debit-a",
            SepaCollectionStatus.SUCCEEDED,
        )
    )
    assert succeeded.status is SepaCollectionStatus.SUCCEEDED


def test_duplicate_provider_event_is_idempotent(tmp_path) -> None:
    store = store_with_collection(tmp_path)
    service = SepaReconciliationService(store)
    event = SepaProviderEvent(
        "provider-a",
        "provider-debit-a",
        SepaCollectionStatus.PENDING,
    )

    first = service.apply(event)
    second = service.apply(event)

    assert first == second


def test_foreign_provider_event_cannot_mutate_collection(tmp_path) -> None:
    store = store_with_collection(tmp_path)
    service = SepaReconciliationService(store)

    with pytest.raises(KeyError):
        service.apply(
            SepaProviderEvent(
                "provider-b",
                "provider-debit-a",
                SepaCollectionStatus.SUCCEEDED,
            )
        )

    assert store.get("collection-a").status is SepaCollectionStatus.SUBMITTED


def test_return_event_requires_prior_success(tmp_path) -> None:
    store = store_with_collection(tmp_path)
    service = SepaReconciliationService(store)

    with pytest.raises(ValueError, match="cannot transition"):
        service.apply(
            SepaProviderEvent(
                "provider-a",
                "provider-debit-a",
                SepaCollectionStatus.RETURNED,
            )
        )
