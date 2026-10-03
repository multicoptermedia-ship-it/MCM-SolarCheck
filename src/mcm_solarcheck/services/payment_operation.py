"""Persistent intent boundary for mutually exclusive terminal payment operations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class PaymentOperation(str, Enum):
    CAPTURE = "capture"
    VOID = "void"


class PaymentOperationStatus(str, Enum):
    RESERVED = "reserved"
    PROVIDER_SUCCEEDED = "provider_succeeded"
    COMPLETED = "completed"


@dataclass(frozen=True)
class PaymentOperationIntent:
    payment_id: str
    operation: PaymentOperation
    idempotency_key: str
    status: PaymentOperationStatus = PaymentOperationStatus.RESERVED

    def __post_init__(self) -> None:
        if not isinstance(self.payment_id, str) or not self.payment_id.strip():
            raise ValueError("payment_id must be non-empty")
        if not isinstance(self.operation, PaymentOperation):
            raise ValueError("operation must be PaymentOperation")
        if not isinstance(self.idempotency_key, str) or not self.idempotency_key.strip():
            raise ValueError("idempotency_key must be non-empty")
        if not isinstance(self.status, PaymentOperationStatus):
            raise ValueError("status must be PaymentOperationStatus")


class PaymentOperationIntentStore(Protocol):
    def reserve(self, intent: PaymentOperationIntent) -> PaymentOperationIntent:
        """Atomically reserve the one terminal provider operation for a payment."""
        ...

    def mark_provider_succeeded(self, payment_id: str) -> PaymentOperationIntent:
        ...

    def mark_completed(self, payment_id: str) -> PaymentOperationIntent:
        ...

    def get(self, payment_id: str) -> PaymentOperationIntent:
        ...
