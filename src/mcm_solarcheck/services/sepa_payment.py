"""Provider-neutral SEPA payment submission boundary."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from mcm_solarcheck.services.billing import ComputeJobBillingStore

from mcm_solarcheck.services.payment import OnlinePayment, OnlinePaymentStore, PaymentStatus
from mcm_solarcheck.services.payment_methods import PaymentMethod
from mcm_solarcheck.services.sepa import SepaMandate, SepaMandateStatus
from mcm_solarcheck.services.sepa_collection import SepaCollection
from mcm_solarcheck.services.sepa_submission import SepaSubmission, SepaSubmissionStatus


class SepaMandateStore(Protocol):
    def get(self, mandate_id: str) -> SepaMandate:
        ...


class SepaSubmissionStore(Protocol):
    def reserve(
        self, submission: SepaSubmission, *, now: datetime
    ) -> SepaSubmission:
        ...

    def mark_submitted(
        self, payment_id: str, provider_reference: str, lease_token: str
    ) -> SepaSubmission:
        ...

    def release(self, payment_id: str, lease_token: str) -> None:
        ...


class SepaCollectionStore(Protocol):
    def create(self, collection: SepaCollection) -> None:
        ...


class SepaPaymentGateway(Protocol):
    def submit(
        self,
        payment: OnlinePayment,
        mandate_reference: str,
        *,
        idempotency_key: str,
    ) -> str:
        ...


def sepa_submission_key(payment_id: str) -> str:
    if not isinstance(payment_id, str) or not payment_id.strip():
        raise ValueError("payment_id must be non-empty")
    return f"payment:{payment_id.strip()}:sepa-submit"


class SepaPaymentService:
    def __init__(
        self,
        payments: OnlinePaymentStore,
        mandates: SepaMandateStore,
        gateway: SepaPaymentGateway,
        provider_id: str,
        collections: SepaCollectionStore | None = None,
        submissions: SepaSubmissionStore | None = None,
        *,
        billing: ComputeJobBillingStore,
    ) -> None:
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise ValueError("provider_id must be non-empty")
        self._payments = payments
        self._mandates = mandates
        self._gateway = gateway
        self._provider_id = provider_id.strip()
        self._collections = collections
        self._submissions = submissions
        self._billing = billing

    def submit(
        self,
        payment_id: str,
        mandate_id: str,
        *,
        user_id: str,
        project_id: str,
    ) -> str:
        payment = self._payments.get(payment_id)
        if payment.user_id != user_id or payment.project_id != project_id:
            raise PermissionError("payment ownership mismatch")
        if payment.method is not PaymentMethod.SEPA_DIRECT_DEBIT:
            raise ValueError("SEPA submission requires SEPA payment method")
        if payment.status is not PaymentStatus.CREATED:
            raise ValueError("SEPA submission requires created payment")
        if payment.amount is None:
            raise ValueError("SEPA submission requires payable amount")

        billing = self._billing.get(payment.job_id)
        if (
            billing.delivery.user_id != payment.user_id
            or billing.delivery.project_id != payment.project_id
        ):
            raise PermissionError("payment billing identity mismatch")
        if not billing.delivery.billable:
            raise ValueError(
                "export and report retrieval are required before SEPA submission"
            )
        if not billing.billing_released:
            raise ValueError(
                "billing must be released before SEPA submission"
            )

        mandate = self._mandates.get(mandate_id)
        if mandate.user_id != user_id:
            raise PermissionError("SEPA mandate ownership mismatch")
        if mandate.provider_id != self._provider_id:
            raise ValueError("SEPA mandate provider mismatch")
        if mandate.status is not SepaMandateStatus.ACTIVE:
            raise ValueError("SEPA submission requires active mandate")
        if mandate.provider_reference is None:
            raise ValueError("active SEPA mandate requires provider reference")

        idempotency_key = sepa_submission_key(payment_id)
        reserved = None
        if self._submissions is not None:
            reserved = self._submissions.reserve(
                SepaSubmission(
                    payment_id,
                    mandate_id,
                    user_id,
                    project_id,
                    self._provider_id,
                    idempotency_key,
                ),
                now=datetime.now(timezone.utc),
            )
            if reserved.status is SepaSubmissionStatus.SUBMITTED:
                return reserved.provider_reference
            if reserved.lease_token is None:
                raise RuntimeError("claimed SEPA submission has no lease token")

        try:
            provider_reference = self._gateway.submit(
                payment,
                mandate.provider_reference,
                idempotency_key=idempotency_key,
            )
            if self._submissions is not None:
                self._submissions.mark_submitted(
                    payment_id,
                    provider_reference,
                    reserved.lease_token,
                )
        except Exception:
            if self._submissions is not None and reserved is not None:
                try:
                    self._submissions.release(payment_id, reserved.lease_token)
                except ValueError:
                    pass
            raise
        if self._collections is not None:
            try:
                self._collections.create(
                    SepaCollection(
                        f"sepa:{payment_id}",
                        payment_id,
                        user_id,
                        project_id,
                        self._provider_id,
                        provider_reference,
                    )
                )
            except Exception:
                # A retry may encounter the collection created by an earlier
                # attempt. The submission intent remains the source of truth.
                existing = getattr(self._collections, "get", lambda _: None)(
                    f"sepa:{payment_id}"
                )
                if (
                    existing is None
                    or existing.provider_reference != provider_reference
                ):
                    raise
        return provider_reference
