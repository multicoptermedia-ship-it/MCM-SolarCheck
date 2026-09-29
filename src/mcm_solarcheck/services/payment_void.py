"""Server-owned release of an external payment authorization."""

from __future__ import annotations

from mcm_solarcheck.services.payment import OnlinePayment, OnlinePaymentStore, PaymentStatus
from mcm_solarcheck.services.payment_gateway import PaymentGateway, payment_idempotency_key


class PaymentVoidService:
    """Void an authorization at the provider before marking it void locally."""

    def __init__(self, payments: OnlinePaymentStore, gateway: PaymentGateway) -> None:
        self._payments = payments
        self._gateway = gateway

    def void(
        self, payment_id: str, *, user_id: str, project_id: str
    ) -> OnlinePayment:
        payment = self._payments.get(payment_id)
        if payment.user_id != user_id or payment.project_id != project_id:
            raise PermissionError("payment ownership mismatch")
        if payment.status is not PaymentStatus.AUTHORIZED:
            raise ValueError("payment void requires authorized state")
        if payment.provider_reference is None:
            raise ValueError("authorized payment requires provider reference")

        self._gateway.void(
            payment.provider_reference,
            idempotency_key=payment_idempotency_key(payment_id, "void"),
        )
        return self._payments.void(payment_id, user_id, project_id)
