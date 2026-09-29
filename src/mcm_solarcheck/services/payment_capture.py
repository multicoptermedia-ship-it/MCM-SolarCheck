"""Server-side capture gate between payment authorization and billing evidence."""

from __future__ import annotations

from mcm_solarcheck.services.billing import ComputeJobBillingStore
from mcm_solarcheck.services.payment import OnlinePayment, OnlinePaymentStore, PaymentStatus
from mcm_solarcheck.services.payment_gateway import PaymentGateway, payment_idempotency_key
from mcm_solarcheck.services.payment_operation import (
    PaymentOperation,
    PaymentOperationIntent,
    PaymentOperationIntentStore,
)


class PaymentCaptureService:
    """Capture only an authorized payment for released delivered work."""

    def __init__(
        self,
        payment_store: OnlinePaymentStore,
        billing_store: ComputeJobBillingStore,
        gateway: PaymentGateway | None = None,
        operation_intents: PaymentOperationIntentStore | None = None,
    ) -> None:
        self._payments = payment_store
        self._billing = billing_store
        self._gateway = gateway
        self._operation_intents = operation_intents
        if gateway is not None and operation_intents is None:
            raise ValueError(
                "provider capture requires persistent operation intents"
            )

    def capture(
        self,
        payment_id: str,
        *,
        user_id: str,
        project_id: str,
    ) -> OnlinePayment:
        payment = self._payments.get(payment_id)
        if payment.user_id != user_id or payment.project_id != project_id:
            raise PermissionError("payment ownership mismatch")
        if payment.status is not PaymentStatus.AUTHORIZED:
            raise ValueError("payment capture requires authorized state")

        billing = self._billing.get(payment.job_id)
        if (
            billing.delivery.user_id != payment.user_id
            or billing.delivery.project_id != payment.project_id
        ):
            raise PermissionError("payment billing identity mismatch")
        if not billing.delivery.billable:
            raise ValueError(
                "export and report retrieval are required before payment capture"
            )
        if not billing.billing_released:
            raise ValueError("billing must be released before payment capture")

        if self._gateway is not None:
            if payment.provider_reference is None:
                raise ValueError("authorized payment requires provider reference")
            key = payment_idempotency_key(payment_id, "capture")
            intent = self._operation_intents.reserve(
                PaymentOperationIntent(payment_id, PaymentOperation.CAPTURE, key)
            )
            if intent.status.value == "reserved":
                self._gateway.capture(
                    payment.provider_reference,
                    idempotency_key=key,
                )
                self._operation_intents.mark_provider_succeeded(payment_id)

            updated = self._payments.capture(payment_id, user_id, project_id)
            if self._operation_intents is not None:
                self._operation_intents.mark_completed(payment_id)
            return updated
