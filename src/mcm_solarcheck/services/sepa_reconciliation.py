"""Provider-neutral reconciliation of asynchronous SEPA status events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from mcm_solarcheck.services.introductory_offer import IntroductoryOfferStore
from mcm_solarcheck.services.sepa_collection import (
    SepaCollection,
    SepaCollectionStatus,
)


@dataclass(frozen=True)
class SepaProviderEvent:
    provider_id: str
    provider_reference: str
    status: SepaCollectionStatus
    event_id: str | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("provider_id", self.provider_id),
            ("provider_reference", self.provider_reference),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if self.event_id is not None and (
            not isinstance(self.event_id, str) or not self.event_id.strip()
        ):
            raise ValueError("event_id must be non-empty when configured")
        if self.status is SepaCollectionStatus.SUBMITTED:
            raise ValueError("provider reconciliation cannot submit collections")


class SepaReconciliationStore(Protocol):
    def get_by_provider_reference(
        self, provider_id: str, provider_reference: str
    ) -> SepaCollection:
        ...

    def transition(
        self,
        collection_id: str,
        *,
        user_id: str,
        target: SepaCollectionStatus,
    ) -> SepaCollection:
        ...

    def apply_provider_event(
        self,
        provider_id: str,
        provider_reference: str,
        *,
        target: SepaCollectionStatus,
    ) -> SepaCollection:
        ...


class SepaReconciliationService:
    def __init__(
        self,
        collections: SepaReconciliationStore,
        introductory_offers: IntroductoryOfferStore | None = None,
    ) -> None:
        self._collections = collections
        self._introductory_offers = introductory_offers

    def resolve(
        self, provider_id: str, provider_reference: str
    ) -> SepaCollection:
        return self._collections.get_by_provider_reference(
            provider_id, provider_reference
        )

    def apply(self, event: SepaProviderEvent) -> SepaCollection:
        atomic_apply = getattr(self._collections, "apply_provider_event", None)
        if callable(atomic_apply):
            result = atomic_apply(
                event.provider_id,
                event.provider_reference,
                target=event.status,
            )
            self._apply_offer_result(result)
            return result

        collection = self._collections.get_by_provider_reference(
            event.provider_id,
            event.provider_reference,
        )
        if collection.status is event.status:
            return collection

        # Non-transactional stores retain the same ordering contract. Durable
        # stores should implement apply_provider_event() so this decision and
        # the state mutation happen under one lock.
        stale_after_terminal = {
            SepaCollectionStatus.SUCCEEDED: {
                SepaCollectionStatus.PENDING,
                SepaCollectionStatus.FAILED,
            },
            SepaCollectionStatus.RETURNED: {
                SepaCollectionStatus.PENDING,
                SepaCollectionStatus.SUCCEEDED,
                SepaCollectionStatus.FAILED,
            },
        }
        if event.status in stale_after_terminal.get(collection.status, set()):
            return collection

        result = self._collections.transition(
            collection.collection_id,
            user_id=collection.user_id,
            target=event.status,
        )
        self._apply_offer_result(result)
        return result

    def _apply_offer_result(self, collection: SepaCollection) -> None:
        if self._introductory_offers is None:
            return
        if collection.status is SepaCollectionStatus.SUCCEEDED:
            try:
                self._introductory_offers.finalize(
                    collection.user_id,
                    collection.payment_id,
                    used_at=datetime.now(timezone.utc),
                )
            except ValueError:
                return
        elif collection.status is SepaCollectionStatus.FAILED:
            self._introductory_offers.release(
                collection.user_id,
                collection.payment_id,
            )
