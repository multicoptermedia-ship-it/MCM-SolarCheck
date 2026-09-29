"""Persistent intent boundary for mutually exclusive terminal payment operations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class PaymentOperation(str, Enum):
    CAPTURE = "capture"
    VOID = "void"


@dataclass(frozen=True)
class PaymentOperationIntent:
    payment_id: str
    operation: PaymentOperation

    def __post_init__(self) -> None:
        if not isinstance(self.payment_id, str) or not self.payment_id.strip():
            raise ValueError("payment_id must be non-empty")
        if not isinstance(self.operation, PaymentOperation):
            raise ValueError("operation must be PaymentOperation")


class PaymentOperationIntentStore(Protocol):
    def reserve(self, intent: PaymentOperationIntent) -> PaymentOperationIntent:
        """Atomically reserve the one terminal provider operation for a payment."""
        ...
