"""Provider-neutral boundary for verified SEPA collection updates."""

from __future__ import annotations

from typing import Protocol

from mcm_solarcheck.services.sepa_collection import (
    SepaCollection,
    SepaCollectionStatus,
)


class SepaCollectionUpdateStore(Protocol):
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


class SepaCollectionUpdateService:
    """Apply a provider event only after the adapter verified its authenticity."""

    def __init__(self, collections: SepaCollectionUpdateStore) -> None:
        for method in ("get_by_provider_reference", "transition"):
            if not callable(getattr(collections, method, None)):
                raise TypeError(f"collections must provide {method}()")
        self._collections = collections

    def apply_verified_update(
        self,
        provider_id: str,
        provider_reference: str,
        target: SepaCollectionStatus,
    ) -> SepaCollection:
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise ValueError("provider_id must be non-empty")
        if not isinstance(provider_reference, str) or not provider_reference.strip():
            raise ValueError("provider_reference must be non-empty")
        if target not in {
            SepaCollectionStatus.PENDING,
            SepaCollectionStatus.SUCCEEDED,
            SepaCollectionStatus.FAILED,
            SepaCollectionStatus.RETURNED,
        }:
            raise ValueError("unsupported SEPA provider update")

        collection = self._collections.get_by_provider_reference(
            provider_id.strip(), provider_reference.strip()
        )
        return self._collections.transition(
            collection.collection_id,
            user_id=collection.user_id,
            target=target,
        )
