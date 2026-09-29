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

    def __post_init__(self) -> None:
        for name, value in (
            ("provider_id", self.provider_id),
            ("provider_reference", self.provider_reference),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
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
