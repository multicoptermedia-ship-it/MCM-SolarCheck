"""Persistent intent for external payment authorization."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class PaymentAuthorizationIntentStatus(str, Enum):
    RESERVED = "reserved"
    PROVIDER_SUCCEEDED = "provider_succeeded"
    COMPLETED = "completed"


@dataclass(frozen=True)
class PaymentAuthorizationIntent:
    payment_id: str
    idempotency_key: str
    status: PaymentAuthorizationIntentStatus = PaymentAuthorizationIntentStatus.RESERVED
    provider_reference: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.payment_id, str) or not self.payment_id.strip():
            raise ValueError("payment_id must be non-empty")
        if not isinstance(self.idempotency_key, str) or not self.idempotency_key.strip():
            raise ValueError("idempotency_key must be non-empty")
        if self.status is PaymentAuthorizationIntentStatus.RESERVED:
            if self.provider_reference is not None:
                raise ValueError("reserved authorization cannot have provider reference")
        elif not isinstance(self.provider_reference, str) or not self.provider_reference.strip():
            raise ValueError("provider reference required after provider success")


class PaymentAuthorizationIntentStore(Protocol):
    def reserve(self, intent: PaymentAuthorizationIntent) -> PaymentAuthorizationIntent: ...
    def mark_provider_succeeded(
        self, payment_id: str, provider_reference: str
    ) -> PaymentAuthorizationIntent: ...
    def mark_completed(self, payment_id: str) -> PaymentAuthorizationIntent: ...
    def get(self, payment_id: str) -> PaymentAuthorizationIntent: ...
