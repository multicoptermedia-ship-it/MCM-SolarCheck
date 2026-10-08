"""Provider-neutral external payment gateway boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from mcm_solarcheck.services.payment import OnlinePayment, OnlinePaymentStore, PaymentStatus
from mcm_solarcheck.services.payment_routing import PaymentProviderRoutingService
from mcm_solarcheck.services.payment_authorization_intent import (
    PaymentAuthorizationIntent,
    PaymentAuthorizationIntentStatus,
    PaymentAuthorizationIntentStore,
)


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

    def __init__(
        self,
        payments: OnlinePaymentStore,
        gateway: PaymentGateway,
        routing: PaymentProviderRoutingService | None = None,
        provider_id: str | None = None,
        intents: PaymentAuthorizationIntentStore | None = None,
    ) -> None:
        if (routing is None) != (provider_id is None):
            raise ValueError("routing and provider_id must be configured together")
        self._payments = payments
        self._gateway = gateway
        self._routing = routing
        self._provider_id = provider_id
        self._intents = intents

    def authorize(
        self, payment_id: str, *, user_id: str, project_id: str
    ) -> OnlinePayment:
        payment = self._payments.get(payment_id)
        if payment.user_id != user_id or payment.project_id != project_id:
            raise PermissionError("payment ownership mismatch")
        if payment.status is PaymentStatus.SETTLED:
            raise ValueError("settled payment requires no provider authorization")
        if payment.status is PaymentStatus.AUTHORIZED and self._intents is not None:
            try:
                intent = self._intents.get(payment_id)
            except KeyError:
                intent = None
            if (
                intent is not None
                and intent.status is PaymentAuthorizationIntentStatus.COMPLETED
                and intent.provider_reference == payment.provider_reference
            ):
                return payment
        if payment.status is not PaymentStatus.CREATED:
            raise ValueError("payment authorization requires created state")
        if payment.amount is None:
            raise ValueError("provider authorization requires payable amount")

        if self._routing is not None:
            self._routing.require_provider(payment, self._provider_id)

        idempotency_key = payment_idempotency_key(payment_id, "authorize")
        intent = None
        if self._intents is not None:
            intent = self._intents.reserve(
                PaymentAuthorizationIntent(payment_id, idempotency_key)
            )

        if (
            intent is not None
            and intent.status is not PaymentAuthorizationIntentStatus.RESERVED
        ):
            provider_reference = intent.provider_reference
        else:
            result = self._gateway.authorize(
                payment,
                idempotency_key=idempotency_key,
            )
            provider_reference = result.provider_reference
            if self._intents is not None:
                self._intents.mark_provider_succeeded(
                    payment_id, provider_reference
                )

        authorized = self._payments.authorize(
            payment_id,
            user_id,
            project_id,
            provider_reference,
        )
        if self._intents is not None:
            self._intents.mark_completed(payment_id)
        return authorized
