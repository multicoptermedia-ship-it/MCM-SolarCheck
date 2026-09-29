"""Provider-neutral reconciliation of asynchronous SEPA status events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

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
            raise ValueError(\"event_id must be non-empty when configured\")
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


class SepaReconciliationService:
    def __init__(self, collections: SepaReconciliationStore) -> None:
        self._collections = collections

    def resolve(
        self, provider_id: str, provider_reference: str
    ) -> SepaCollection:
        return self._collections.get_by_provider_reference(
            provider_id, provider_reference
        )

    def apply(self, event: SepaProviderEvent) -> SepaCollection:
        collection = self._collections.get_by_provider_reference(
            event.provider_id,
            event.provider_reference,
        )
        if collection.status is event.status:
            return collection

        return self._collections.transition(
            collection.collection_id,
            user_id=collection.user_id,
            target=event.status,
        )
