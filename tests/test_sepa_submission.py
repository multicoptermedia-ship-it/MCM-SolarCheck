from mcm_solarcheck.infrastructure.sqlite_payment import SQLiteOnlinePaymentStore
from mcm_solarcheck.infrastructure.sqlite_sepa import SQLiteSepaMandateStore
from mcm_solarcheck.infrastructure.sqlite_sepa_collection import (
    SQLiteSepaCollectionStore,
)
from mcm_solarcheck.infrastructure.sqlite_sepa_submission import (
    SQLiteSepaSubmissionStore,
)
from mcm_solarcheck.services.payment import OnlinePayment, PaymentAmount
from mcm_solarcheck.services.payment_methods import PaymentMethod
from mcm_solarcheck.services.sepa import SepaMandate
from mcm_solarcheck.services.sepa_payment import SepaPaymentService
from mcm_solarcheck.services.sepa_submission import SepaSubmissionStatus


class IdempotentSepaGateway:
    def __init__(self) -> None:
        self.keys = []

    def submit(self, payment, mandate_reference, *, idempotency_key):
        self.keys.append(idempotency_key)
        return "provider-debit-a"


class FailOnceSubmissionStore:
    def __init__(self, delegate) -> None:
        self.delegate = delegate
        self.failed = False

    def reserve(self, submission):
        return self.delegate.reserve(submission)

    def mark_submitted(self, payment_id, provider_reference):
        if not self.failed:
            self.failed = True
            raise RuntimeError("simulated crash after provider success")
        return self.delegate.mark_submitted(payment_id, provider_reference)


def test_sepa_retry_reuses_reserved_provider_idempotency_key(tmp_path) -> None:
    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    payments.create(
        OnlinePayment(
            "payment-a",
            "user-a",
            "project-a",
            "job-a",
            PaymentAmount(12900, "EUR"),
            method=PaymentMethod.SEPA_DIRECT_DEBIT,
        )
    )
    mandates = SQLiteSepaMandateStore(tmp_path / "mandates.sqlite")
    mandates.create(SepaMandate("mandate-a", "user-a", "provider-a"))
    mandates.activate("mandate-a", "user-a", "provider-mandate-a")

    durable = SQLiteSepaSubmissionStore(tmp_path / "submissions.sqlite")
    submissions = FailOnceSubmissionStore(durable)
    collections = SQLiteSepaCollectionStore(tmp_path / "collections.sqlite")
    gateway = IdempotentSepaGateway()
    service = SepaPaymentService(
        payments,
        mandates,
        gateway,
        "provider-a",
        collections,
        submissions,
    )

    try:
        service.submit(
            "payment-a",
            "mandate-a",
            user_id="user-a",
            project_id="project-a",
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("simulated crash must escape")

    assert durable.get("payment-a").status is SepaSubmissionStatus.PENDING

    service.submit(
        "payment-a",
        "mandate-a",
        user_id="user-a",
        project_id="project-a",
    )

    assert gateway.keys == [
        "payment:payment-a:sepa-submit",
        "payment:payment-a:sepa-submit",
    ]
    assert durable.get("payment-a").status is SepaSubmissionStatus.SUBMITTED
    assert collections.get("sepa:payment-a").provider_reference == "provider-debit-a"
