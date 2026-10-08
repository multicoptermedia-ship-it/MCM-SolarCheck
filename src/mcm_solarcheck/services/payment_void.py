"""Server-owned release of an external payment authorization."""

from __future__ import annotations

from mcm_solarcheck.services.introductory_offer import IntroductoryOfferStore
from mcm_solarcheck.services.payment import OnlinePayment, OnlinePaymentStore, PaymentStatus
from mcm_solarcheck.services.payment_gateway import PaymentGateway, payment_idempotency_key
from mcm_solarcheck.services.payment_methods import payment_method_capabilities
from mcm_solarcheck.services.payment_operation import (
    PaymentOperation,
    PaymentOperationIntent,
    PaymentOperationIntentStore,
    PaymentOperationStatus,
)


class PaymentVoidService:
    """Void an authorization at the provider before marking it void locally."""

    def __init__(
        self,
        payments: OnlinePaymentStore,
        gateway: PaymentGateway,
        operation_intents: PaymentOperationIntentStore,
        introductory_offers: IntroductoryOfferStore | None = None,
    ) -> None:
        self._payments = payments
        self._gateway = gateway
        self._operation_intents = operation_intents
        self._introductory_offers = introductory_offers

    def void(
        self, payment_id: str, *, user_id: str, project_id: str
    ) -> OnlinePayment:
        payment = self._payments.get(payment_id)
        if payment.user_id != user_id or payment.project_id != project_id:
            raise PermissionError("payment ownership mismatch")
        if payment.status is PaymentStatus.VOIDED:
            intent = self._operation_intents.get(payment_id)
            if (
                intent.operation is PaymentOperation.VOID
                and intent.status is PaymentOperationStatus.PROVIDER_SUCCEEDED
            ):
                self._operation_intents.mark_completed(payment_id)
                if self._introductory_offers is not None:
                    self._introductory_offers.release(user_id, payment_id)
                return payment
            if (
                intent.operation is PaymentOperation.VOID
                and intent.status is PaymentOperationStatus.COMPLETED
            ):
                if self._introductory_offers is not None:
                    self._introductory_offers.release(user_id, payment_id)
                return payment
            raise ValueError("voided payment has inconsistent operation intent")
        if payment.status is not PaymentStatus.AUTHORIZED:
            raise ValueError("payment void requires authorized state")
        if payment.method is not None and not payment_method_capabilities(
            payment.method
        ).supports_void:
            raise ValueError("payment method does not support void")
        if payment.provider_reference is None:
            raise ValueError("authorized payment requires provider reference")

        key = payment_idempotency_key(payment_id, "void")
        intent = self._operation_intents.reserve(
            PaymentOperationIntent(payment_id, PaymentOperation.VOID, key)
        )
        if intent.status is PaymentOperationStatus.RESERVED:
            self._gateway.void(
                payment.provider_reference,
                idempotency_key=key,
            )
            self._operation_intents.mark_provider_succeeded(payment_id)
        updated = self._payments.void(payment_id, user_id, project_id)
        if self._operation_intents is not None:
            self._operation_intents.mark_completed(payment_id)
        if self._introductory_offers is not None:
            self._introductory_offers.release(user_id, payment_id)
        return updated
