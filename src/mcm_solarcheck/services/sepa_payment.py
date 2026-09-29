"""Provider-neutral SEPA payment submission boundary."""

from __future__ import annotations

from typing import Protocol

from mcm_solarcheck.services.payment import OnlinePayment, OnlinePaymentStore, PaymentStatus
from mcm_solarcheck.services.payment_methods import PaymentMethod
from mcm_solarcheck.services.sepa import SepaMandate, SepaMandateStatus
from mcm_solarcheck.services.sepa_collection import SepaCollection
from mcm_solarcheck.services.sepa_submission import SepaSubmission


class SepaMandateStore(Protocol):
    def get(self, mandate_id: str) -> SepaMandate:
        ...


class SepaSubmissionStore(Protocol):
    def reserve(self, submission: SepaSubmission) -> SepaSubmission:
        ...

    def mark_submitted(
        self, payment_id: str, provider_reference: str
    ) -> SepaSubmission:
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
    ) -> None:
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise ValueError("provider_id must be non-empty")
        self._payments = payments
        self._mandates = mandates
        self._gateway = gateway
        self._provider_id = provider_id.strip()
        self._collections = collections
        self._submissions = submissions

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
        if self._submissions is not None:
            self._submissions.reserve(
                SepaSubmission(
                    payment_id,
                    mandate_id,
                    user_id,
                    project_id,
                    self._provider_id,
                    idempotency_key,
                )
            )

        provider_reference = self._gateway.submit(
            payment,
            mandate.provider_reference,
            idempotency_key=idempotency_key,
        )
        if self._submissions is not None:
            self._submissions.mark_submitted(payment_id, provider_reference)
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
