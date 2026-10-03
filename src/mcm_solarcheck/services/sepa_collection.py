"""Server-owned asynchronous SEPA collection lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class SepaCollectionStatus(str, Enum):
    SUBMITTED = "submitted"
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETURNED = "returned"


@dataclass(frozen=True)
class SepaCollection:
    collection_id: str
    payment_id: str
    user_id: str
    project_id: str
    provider_id: str
    provider_reference: str
    status: SepaCollectionStatus = SepaCollectionStatus.SUBMITTED

    def __post_init__(self) -> None:
        for name, value in (
            ("collection_id", self.collection_id),
            ("payment_id", self.payment_id),
            ("user_id", self.user_id),
            ("project_id", self.project_id),
            ("provider_id", self.provider_id),
            ("provider_reference", self.provider_reference),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")

    def pending(self) -> "SepaCollection":
        return self._transition(
            SepaCollectionStatus.PENDING,
            {SepaCollectionStatus.SUBMITTED},
        )

    def succeed(self) -> "SepaCollection":
        return self._transition(
            SepaCollectionStatus.SUCCEEDED,
            {SepaCollectionStatus.SUBMITTED, SepaCollectionStatus.PENDING},
        )

    def fail(self) -> "SepaCollection":
        return self._transition(
            SepaCollectionStatus.FAILED,
            {SepaCollectionStatus.SUBMITTED, SepaCollectionStatus.PENDING},
        )

    def returned(self) -> "SepaCollection":
        return self._transition(
            SepaCollectionStatus.RETURNED,
            {SepaCollectionStatus.SUCCEEDED},
        )

    def _transition(
        self,
        target: SepaCollectionStatus,
        allowed: set[SepaCollectionStatus],
    ) -> "SepaCollection":
        if self.status not in allowed:
            raise ValueError(
                f"SEPA collection cannot transition from {self.status.value} "
                f"to {target.value}"
            )
        return SepaCollection(
            self.collection_id,
            self.payment_id,
            self.user_id,
            self.project_id,
            self.provider_id,
            self.provider_reference,
            target,
        )



class SepaCollectionPersistence(Protocol):
    """Persistence for asynchronous SEPA collection and reconciliation."""

    def create(self, collection: SepaCollection) -> None:
        ...

    def get(self, collection_id: str) -> SepaCollection:
        ...

    def get_by_provider_reference(
        self, provider_id: str, provider_reference: str
    ) -> SepaCollection:
        ...

    def apply_provider_event(
        self,
        provider_id: str,
        provider_reference: str,
        *,
        target: SepaCollectionStatus,
    ) -> SepaCollection:
        """Apply provider event ordering atomically with the durable transition."""
        ...

    def transition(
        self,
        collection_id: str,
        *,
        user_id: str,
        target: SepaCollectionStatus,
    ) -> SepaCollection:
        ...
