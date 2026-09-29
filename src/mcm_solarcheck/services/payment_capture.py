"""Server-side capture gate between payment authorization and billing evidence."""

from __future__ import annotations

from typing import Protocol

from mcm_solarcheck.services.billing import ComputeJobBillingStore
from mcm_solarcheck.services.payment import OnlinePayment, PaymentStatus


class PaymentStore(Protocol):
    def get(self, payment_id: str) -> OnlinePayment:
        ...

    def replace(self, payment: OnlinePayment) -> None:
        ...


class PaymentCaptureService:
    """Capture only an authorized payment for released delivered work."""

    def __init__(
        self,
        payment_store: PaymentStore,
        billing_store: ComputeJobBillingStore,
    ) -> None:
        self._payments = payment_store
        self._billing = billing_store

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
        if not billing.billing_released:
            raise ValueError("billing must be released before payment capture")

        captured = payment.capture()
        self._payments.replace(captured)
        return captured
