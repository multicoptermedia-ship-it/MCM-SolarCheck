"""Provider-neutral external payment gateway boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from mcm_solarcheck.services.payment import OnlinePayment, OnlinePaymentStore, PaymentStatus


@dataclass(frozen=True)
class PaymentAuthorizationResult:
    provider_reference: str

    def __post_init__(self) -> None:
        if not isinstance(self.provider_reference, str) or not self.provider_reference.strip():
            raise ValueError("provider_reference must be non-empty")


def payment_idempotency_key(payment_id: str, operation: str) -> str:
    if not isinstance(payment_id, str) or not payment_id.strip():
        raise ValueError("payment_id must be non-empty")
    if operation not in {"authorize", "capture", "void"}:
        raise ValueError("unsupported payment operation")
    return f"payment:{payment_id.strip()}:{operation}"


class PaymentGateway(Protocol):
    def authorize(
        self, payment: OnlinePayment, *, idempotency_key: str
    ) -> PaymentAuthorizationResult:
        """Reserve the payment amount without capturing it."""
        ...

    def capture(
        self, provider_reference: str, *, idempotency_key: str
    ) -> None:
        """Capture a previously authorized provider payment."""
        ...

    def void(
        self, provider_reference: str, *, idempotency_key: str
    ) -> None:
        """Release a previously authorized provider payment."""
        ...


class PaymentAuthorizationService:
    """Authorize only payable created payments and persist provider identity."""

    def __init__(self, payments: OnlinePaymentStore, gateway: PaymentGateway) -> None:
        self._payments = payments
        self._gateway = gateway

    def authorize(
        self, payment_id: str, *, user_id: str, project_id: str
    ) -> OnlinePayment:
        payment = self._payments.get(payment_id)
        if payment.user_id != user_id or payment.project_id != project_id:
            raise PermissionError("payment ownership mismatch")
        if payment.status is PaymentStatus.SETTLED:
            raise ValueError("settled payment requires no provider authorization")
        if payment.status is not PaymentStatus.CREATED:
            raise ValueError("payment authorization requires created state")
        if payment.amount is None:
            raise ValueError("provider authorization requires payable amount")

        result = self._gateway.authorize(
            payment,
            idempotency_key=payment_idempotency_key(payment_id, "authorize"),
        )
        return self._payments.authorize(
            payment_id,
            user_id,
            project_id,
            result.provider_reference,
        )
