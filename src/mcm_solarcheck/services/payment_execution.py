"""Provider-neutral evidence that payable work reached payment execution."""

from __future__ import annotations

from typing import Protocol

from mcm_solarcheck.services.payment import OnlinePayment, PaymentStatus
from mcm_solarcheck.services.payment_methods import PaymentMethod
from mcm_solarcheck.services.sepa_submission import SepaSubmission, SepaSubmissionStatus


class SepaSubmissionEvidenceStore(Protocol):
    def get(self, payment_id: str) -> SepaSubmission:
        ...


class PaymentExecutionEvidence:
    """Require durable provider execution evidence before invoicing."""

    def __init__(self, sepa_submissions: SepaSubmissionEvidenceStore) -> None:
        if not callable(getattr(sepa_submissions, "get", None)):
            raise TypeError("sepa_submissions must provide get()")
        self._sepa_submissions = sepa_submissions

    def require_succeeded(self, payment: OnlinePayment) -> None:
        if payment.method is PaymentMethod.SEPA_DIRECT_DEBIT:
            try:
                submission = self._sepa_submissions.get(payment.payment_id)
            except KeyError as exc:
                raise ValueError("invoice requires submitted SEPA payment") from exc
            if (
                submission.status is not SepaSubmissionStatus.SUBMITTED
                or not submission.provider_reference
            ):
                raise ValueError("invoice requires submitted SEPA payment")
            if (
                submission.payment_id != payment.payment_id
                or submission.user_id != payment.user_id
                or submission.project_id != payment.project_id
            ):
                raise PermissionError("SEPA payment evidence identity mismatch")
            return

        if payment.method in (PaymentMethod.CARD, PaymentMethod.PAYPAL):
            if payment.status is not PaymentStatus.CAPTURED:
                raise ValueError("invoice requires captured payment")
            return

        raise ValueError("invoice requires configured payment method")
