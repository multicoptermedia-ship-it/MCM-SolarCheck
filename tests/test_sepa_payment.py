import pytest

from mcm_solarcheck.infrastructure.sqlite_payment import SQLiteOnlinePaymentStore
from mcm_solarcheck.infrastructure.sqlite_sepa import SQLiteSepaMandateStore
from mcm_solarcheck.services.payment import OnlinePayment, PaymentAmount
from mcm_solarcheck.services.payment_methods import PaymentMethod
from mcm_solarcheck.services.sepa import SepaMandate
from mcm_solarcheck.services.sepa_payment import SepaPaymentService


class RecordingSepaGateway:
    def __init__(self) -> None:
        self.calls = []

    def submit(
        self, payment, mandate_reference, *, idempotency_key
    ) -> str:
        self.calls.append((payment, mandate_reference, idempotency_key))
        return "provider-debit-a"


def setup_payment(tmp_path):
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
    mandates = SQLiteSepaMandateStore(tmp_path / "sepa.sqlite")
    mandates.create(SepaMandate("mandate-a", "user-a", "provider-a"))
    return payments, mandates


def test_sepa_submission_requires_active_matching_mandate(tmp_path) -> None:
    payments, mandates = setup_payment(tmp_path)
    gateway = RecordingSepaGateway()
    service = SepaPaymentService(
        payments, mandates, gateway, "provider-a"
    )

    with pytest.raises(ValueError, match="active mandate"):
        service.submit(
            "payment-a",
            "mandate-a",
            user_id="user-a",
            project_id="project-a",
        )
    assert gateway.calls == []

    mandates.activate("mandate-a", "user-a", "provider-mandate-a")
    reference = service.submit(
        "payment-a",
        "mandate-a",
        user_id="user-a",
        project_id="project-a",
    )

    assert reference == "provider-debit-a"
    assert gateway.calls[0][1:] == (
        "provider-mandate-a",
        "payment:payment-a:sepa-submit",
    )


def test_sepa_submission_rejects_cross_user_mandate(tmp_path) -> None:
    payments, mandates = setup_payment(tmp_path)
    mandates.create(SepaMandate("mandate-b", "user-b", "provider-a"))
    mandates.activate("mandate-b", "user-b", "provider-mandate-b")
    gateway = RecordingSepaGateway()

    with pytest.raises(PermissionError, match="mandate ownership"):
        SepaPaymentService(
            payments, mandates, gateway, "provider-a"
        ).submit(
            "payment-a",
            "mandate-b",
            user_id="user-a",
            project_id="project-a",
        )

    assert gateway.calls == []
