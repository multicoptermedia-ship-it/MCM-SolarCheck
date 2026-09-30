from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.sqlite_billing import SQLiteComputeJobBillingStore
from mcm_solarcheck.infrastructure.sqlite_payment import SQLiteOnlinePaymentStore
from mcm_solarcheck.infrastructure.sqlite_sepa import SQLiteSepaMandateStore
from mcm_solarcheck.infrastructure.sqlite_sepa_submission import SQLiteSepaSubmissionStore
from mcm_solarcheck.services.billing import ComputeJobBillingService
from mcm_solarcheck.services.payment import OnlinePayment, PaymentAmount
from mcm_solarcheck.services.payment_methods import PaymentMethod
from mcm_solarcheck.services.report_delivery import ReportArtifact, ReportDeliveryService
from mcm_solarcheck.services.sepa import SepaMandate
from mcm_solarcheck.services.sepa_payment import SepaPaymentService
from mcm_solarcheck.services.sepa_submission import SepaSubmissionStatus


class ReportStore:
    def get(self, job_id: str) -> ReportArtifact:
        return ReportArtifact(
            job_id,
            b"confidential SolarCheck report",
            "application/pdf",
            "solarcheck.pdf",
        )


class RecordingSepaGateway:
    def __init__(self) -> None:
        self.calls = []

    def submit(self, payment, mandate_reference, *, idempotency_key):
        self.calls.append((payment.payment_id, mandate_reference, idempotency_key))
        return "provider-debit-a"


def setup_flow(tmp_path):
    billing_store = SQLiteComputeJobBillingStore(tmp_path / "billing.sqlite")
    billing = ComputeJobBillingService(billing_store)
    billing.create("job-a", user_id="user-a", project_id="project-a")
    billing.mark_export_completed(
        "job-a", user_id="user-a", project_id="project-a"
    )

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

    submissions = SQLiteSepaSubmissionStore(tmp_path / "submissions.sqlite")
    gateway = RecordingSepaGateway()
    sepa = SepaPaymentService(
        payments,
        mandates,
        gateway,
        "provider-a",
        submissions=submissions,
        billing=billing_store,
    )
    delivery = ReportDeliveryService(billing_store, ReportStore())
    return billing_store, gateway, submissions, sepa, delivery


def test_failed_report_delivery_blocks_sepa_submission(tmp_path) -> None:
    billing, gateway, _submissions, sepa, delivery = setup_flow(tmp_path)

    def disconnect(_report: ReportArtifact) -> None:
        raise OSError("client disconnected")

    with pytest.raises(OSError, match="client disconnected"):
        delivery.deliver(
            "job-a",
            user_id="user-a",
            project_id="project-a",
            send=disconnect,
        )

    with pytest.raises(ValueError, match="export and report retrieval"):
        sepa.submit(
            "payment-a",
            "mandate-a",
            user_id="user-a",
            project_id="project-a",
        )

    state = billing.get("job-a")
    assert state.delivery.report_retrieved is False
    assert state.billing_released is False
    assert gateway.calls == []


def test_successful_delivery_allows_idempotent_sepa_submission(tmp_path) -> None:
    billing, gateway, submissions, sepa, delivery = setup_flow(tmp_path)

    delivery.deliver(
        "job-a",
        user_id="user-a",
        project_id="project-a",
        send=lambda _report: None,
    )
    first = sepa.submit(
        "payment-a",
        "mandate-a",
        user_id="user-a",
        project_id="project-a",
    )
    second = sepa.submit(
        "payment-a",
        "mandate-a",
        user_id="user-a",
        project_id="project-a",
    )

    state = billing.get("job-a")
    assert state.delivery.report_retrieved is True
    assert state.billing_released is True
    assert first == "provider-debit-a"
    assert second == first
    assert gateway.calls == [
        (
            "payment-a",
            "provider-mandate-a",
            "payment:payment-a:sepa-submit",
        )
    ]
    assert submissions.get("payment-a").status is SepaSubmissionStatus.SUBMITTED
