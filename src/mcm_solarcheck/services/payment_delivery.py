"""Orchestrate delivery evidence, billing release, and payment capture."""

from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.billing import ComputeJobBilling, ComputeJobBillingService
from mcm_solarcheck.services.payment import OnlinePayment
from mcm_solarcheck.services.payment_capture import PaymentCaptureService


@dataclass(frozen=True)
class PaymentDeliveryResult:
    billing: ComputeJobBilling
    payment: OnlinePayment | None = None


class PaymentDeliveryService:
    """Capture only after both authoritative delivery conditions are satisfied."""

    def __init__(
        self,
        billing: ComputeJobBillingService,
        capture: PaymentCaptureService,
    ) -> None:
        self._billing = billing
        self._capture = capture

    def mark_export_completed(
        self,
        payment_id: str,
        job_id: str,
        *,
        user_id: str,
        project_id: str,
    ) -> PaymentDeliveryResult:
        billing = self._billing.mark_export_completed(
            job_id,
            user_id=user_id,
            project_id=project_id,
        )
        return self._release_and_capture_if_ready(
            payment_id,
            billing,
            user_id=user_id,
            project_id=project_id,
        )

    def mark_report_retrieved(
        self,
        payment_id: str,
        job_id: str,
        *,
        user_id: str,
        project_id: str,
    ) -> PaymentDeliveryResult:
        billing = self._billing.mark_report_retrieved(
            job_id,
            user_id=user_id,
            project_id=project_id,
        )
        return self._release_and_capture_if_ready(
            payment_id,
            billing,
            user_id=user_id,
            project_id=project_id,
        )

    def _release_and_capture_if_ready(
        self,
        payment_id: str,
        billing: ComputeJobBilling,
        *,
        user_id: str,
        project_id: str,
    ) -> PaymentDeliveryResult:
        if not billing.delivery.billable:
            return PaymentDeliveryResult(billing)

        if not billing.billing_released:
            billing = self._billing.release(
                billing.delivery.job_id,
                user_id=user_id,
                project_id=project_id,
            )

        payment = self._capture.capture(
            payment_id,
            user_id=user_id,
            project_id=project_id,
        )
        return PaymentDeliveryResult(billing, payment)
