import pytest

from mcm_solarcheck.services.sepa_collection import (
    SepaCollection,
    SepaCollectionStatus,
)


def collection() -> SepaCollection:
    return SepaCollection(
        "collection-a",
        "payment-a",
        "user-a",
        "project-a",
        "provider-a",
        "provider-debit-a",
    )


def test_sepa_collection_is_not_successful_when_submitted() -> None:
    item = collection()
    assert item.status is SepaCollectionStatus.SUBMITTED

    pending = item.pending()
    assert pending.status is SepaCollectionStatus.PENDING

    succeeded = pending.succeed()
    assert succeeded.status is SepaCollectionStatus.SUCCEEDED


def test_failed_collection_cannot_be_marked_successful() -> None:
    failed = collection().fail()

    with pytest.raises(ValueError, match="cannot transition"):
        failed.succeed()


def test_successful_collection_can_later_be_returned() -> None:
    returned = collection().succeed().returned()
    assert returned.status is SepaCollectionStatus.RETURNED
