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


class PaymentGateway(Protocol):
    def authorize(self, payment: OnlinePayment) -> PaymentAuthorizationResult:
        """Reserve the payment amount without capturing it."""
        ...

    def capture(self, provider_reference: str) -> None:
        """Capture a previously authorized provider payment."""
        ...

    def void(self, provider_reference: str) -> None:
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

        result = self._gateway.authorize(payment)
        return self._payments.authorize(
            payment_id,
            user_id,
            project_id,
            result.provider_reference,
        )
