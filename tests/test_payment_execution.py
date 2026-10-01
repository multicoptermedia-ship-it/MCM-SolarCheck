from __future__ import annotations

from dataclasses import replace

import pytest

from mcm_solarcheck.services.payment import OnlinePayment, PaymentAmount, PaymentStatus
from mcm_solarcheck.services.payment_execution import PaymentExecutionEvidence
from mcm_solarcheck.services.payment_methods import PaymentMethod
from mcm_solarcheck.services.sepa_submission import SepaSubmission


class SubmissionStore:
    def __init__(self, submission=None) -> None:
        self.submission = submission

    def get(self, payment_id: str):
        if self.submission is None or self.submission.payment_id != payment_id:
            raise KeyError(payment_id)
        return self.submission


def payment(method: PaymentMethod, status: PaymentStatus = PaymentStatus.CREATED):
    return OnlinePayment(
        "payment-a", "user-a", "project-a", "job-a",
        PaymentAmount(12900, "EUR"), status=status, method=method,
    )


@pytest.mark.parametrize("method", [PaymentMethod.CARD, PaymentMethod.PAYPAL])
def test_card_like_payment_requires_capture(method) -> None:
    evidence = PaymentExecutionEvidence(SubmissionStore())

    with pytest.raises(ValueError, match="captured payment"):
        evidence.require_succeeded(payment(method))

    evidence.require_succeeded(payment(method, PaymentStatus.CAPTURED))


def test_sepa_requires_persisted_submitted_provider_evidence() -> None:
    pending = SepaSubmission(
        "payment-a", "mandate-a", "user-a", "project-a", "provider-a",
        "payment:payment-a:sepa-submit",
    )
    evidence = PaymentExecutionEvidence(SubmissionStore(pending))
    sepa = payment(PaymentMethod.SEPA_DIRECT_DEBIT)

    with pytest.raises(ValueError, match="submitted SEPA"):
        evidence.require_succeeded(sepa)

    submitted = pending.submitted("provider-debit-a")
    PaymentExecutionEvidence(SubmissionStore(submitted)).require_succeeded(sepa)


def test_sepa_evidence_identity_must_match_payment() -> None:
    submitted = SepaSubmission(
        "payment-a", "mandate-a", "user-a", "project-b", "provider-a",
        "payment:payment-a:sepa-submit",
    ).submitted("provider-debit-a")

    with pytest.raises(PermissionError, match="evidence identity"):
        PaymentExecutionEvidence(SubmissionStore(submitted)).require_succeeded(
            payment(PaymentMethod.SEPA_DIRECT_DEBIT)
        )


def test_payment_without_configured_method_is_not_invoice_evidence() -> None:
    unconfigured = OnlinePayment(
        "payment-a", "user-a", "project-a", "job-a", PaymentAmount(12900, "EUR")
    )

    with pytest.raises(ValueError, match="configured payment method"):
        PaymentExecutionEvidence(SubmissionStore()).require_succeeded(unconfigured)


def test_payment_execution_evidence_requires_sepa_store() -> None:
    with pytest.raises(TypeError, match="sepa_submissions must provide get"):
        PaymentExecutionEvidence(object())
