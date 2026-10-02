from concurrent.futures import ThreadPoolExecutor

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



def test_stale_pending_after_success_does_not_regress_collection(tmp_path) -> None:
    store = store_with_collection(tmp_path)
    service = SepaReconciliationService(store)

    service.apply(
        SepaProviderEvent(
            "provider-a",
            "provider-debit-a",
            SepaCollectionStatus.SUCCEEDED,
        )
    )
    result = service.apply(
        SepaProviderEvent(
            "provider-a",
            "provider-debit-a",
            SepaCollectionStatus.PENDING,
        )
    )

    assert result.status is SepaCollectionStatus.SUCCEEDED
    assert store.get("collection-a").status is SepaCollectionStatus.SUCCEEDED


def test_stale_failure_after_success_does_not_regress_collection(tmp_path) -> None:
    store = store_with_collection(tmp_path)
    service = SepaReconciliationService(store)

    service.apply(
        SepaProviderEvent(
            "provider-a",
            "provider-debit-a",
            SepaCollectionStatus.SUCCEEDED,
        )
    )
    result = service.apply(
        SepaProviderEvent(
            "provider-a",
            "provider-debit-a",
            SepaCollectionStatus.FAILED,
        )
    )

    assert result.status is SepaCollectionStatus.SUCCEEDED
    assert store.get("collection-a").status is SepaCollectionStatus.SUCCEEDED


def test_returned_is_terminal_against_stale_provider_events(tmp_path) -> None:
    store = store_with_collection(tmp_path)
    service = SepaReconciliationService(store)

    service.apply(
        SepaProviderEvent(
            "provider-a",
            "provider-debit-a",
            SepaCollectionStatus.SUCCEEDED,
        )
    )
    service.apply(
        SepaProviderEvent(
            "provider-a",
            "provider-debit-a",
            SepaCollectionStatus.RETURNED,
        )
    )

    for stale_status in (
        SepaCollectionStatus.PENDING,
        SepaCollectionStatus.SUCCEEDED,
        SepaCollectionStatus.FAILED,
    ):
        result = service.apply(
            SepaProviderEvent(
                "provider-a",
                "provider-debit-a",
                stale_status,
            )
        )
        assert result.status is SepaCollectionStatus.RETURNED

    assert store.get("collection-a").status is SepaCollectionStatus.RETURNED


def test_concurrent_success_and_stale_pending_converge_to_success(tmp_path) -> None:
    store = store_with_collection(tmp_path)
    service = SepaReconciliationService(store)
    events = (
        SepaProviderEvent(
            "provider-a", "provider-debit-a", SepaCollectionStatus.SUCCEEDED
        ),
        SepaProviderEvent(
            "provider-a", "provider-debit-a", SepaCollectionStatus.PENDING
        ),
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(service.apply, events))

    assert all(
        result.status in {SepaCollectionStatus.PENDING, SepaCollectionStatus.SUCCEEDED}
        for result in results
    )
    assert store.get("collection-a").status is SepaCollectionStatus.SUCCEEDED


def test_concurrent_webhook_and_reconciliation_do_not_regress_success(tmp_path) -> None:
    store = store_with_collection(tmp_path)
    service = SepaReconciliationService(store)
    succeeded = SepaProviderEvent(
        "provider-a", "provider-debit-a", SepaCollectionStatus.SUCCEEDED, "event-success"
    )
    stale_failed = SepaProviderEvent(
        "provider-a", "provider-debit-a", SepaCollectionStatus.FAILED, "event-stale"
    )

    service.apply(succeeded)
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = tuple(
            executor.map(
                service.apply,
                (stale_failed, succeeded, stale_failed, succeeded),
            )
        )

    assert all(result.status is SepaCollectionStatus.SUCCEEDED for result in results)
    assert store.get("collection-a").status is SepaCollectionStatus.SUCCEEDED


def test_concurrent_return_and_stale_events_leave_returned_terminal(tmp_path) -> None:
    store = store_with_collection(tmp_path)
    service = SepaReconciliationService(store)
    service.apply(
        SepaProviderEvent(
            "provider-a", "provider-debit-a", SepaCollectionStatus.SUCCEEDED
        )
    )
    returned = SepaProviderEvent(
        "provider-a", "provider-debit-a", SepaCollectionStatus.RETURNED
    )
    service.apply(returned)

    stale_events = (
        SepaProviderEvent(
            "provider-a", "provider-debit-a", SepaCollectionStatus.PENDING
        ),
        SepaProviderEvent(
            "provider-a", "provider-debit-a", SepaCollectionStatus.SUCCEEDED
        ),
        SepaProviderEvent(
            "provider-a", "provider-debit-a", SepaCollectionStatus.FAILED
        ),
        returned,
    )
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = tuple(executor.map(service.apply, stale_events))

    assert all(result.status is SepaCollectionStatus.RETURNED for result in results)
    assert store.get("collection-a").status is SepaCollectionStatus.RETURNED
