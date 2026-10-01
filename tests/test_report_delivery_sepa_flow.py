from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.sqlite_billing import SQLiteComputeJobBillingStore
from mcm_solarcheck.infrastructure.sqlite_payment import SQLiteOnlinePaymentStore
from mcm_solarcheck.infrastructure.sqlite_sepa import SQLiteSepaMandateStore
from mcm_solarcheck.infrastructure.sqlite_sepa_collection import SQLiteSepaCollectionStore
from mcm_solarcheck.infrastructure.sqlite_sepa_submission import SQLiteSepaSubmissionStore
from mcm_solarcheck.services.billing import ComputeJobBillingService
from mcm_solarcheck.services.payment import OnlinePayment, PaymentAmount
from mcm_solarcheck.services.payment_methods import PaymentMethod
from mcm_solarcheck.services.payment_execution import PaymentExecutionEvidence
from mcm_solarcheck.services.invoice import InvoiceBasisService
from mcm_solarcheck.services.report_delivery import ReportArtifact, ReportDeliveryService
from mcm_solarcheck.services.sepa import SepaMandate
from mcm_solarcheck.services.sepa_collection import SepaCollectionStatus
from mcm_solarcheck.services.sepa_collection_update import SepaCollectionUpdateService
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
    collections = SQLiteSepaCollectionStore(tmp_path / "collections.sqlite")
    gateway = RecordingSepaGateway()
    sepa = SepaPaymentService(
        payments,
        mandates,
        gateway,
        "provider-a",
        collections=collections,
        submissions=submissions,
        billing=billing_store,
    )
    delivery = ReportDeliveryService(billing_store, ReportStore())
    return billing_store, payments, gateway, submissions, collections, sepa, delivery


def test_failed_report_delivery_blocks_sepa_submission(tmp_path) -> None:
    billing, _payments, gateway, _submissions, _collections, sepa, delivery = setup_flow(tmp_path)

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
    billing, _payments, gateway, submissions, sepa, delivery = setup_flow(tmp_path)

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


def test_invoice_basis_requires_successful_sepa_submission_after_delivery(tmp_path) -> None:
    billing, payments, gateway, submissions, _collections, sepa, delivery = setup_flow(tmp_path)
    invoices = InvoiceBasisService(
        billing,
        payments,
        PaymentExecutionEvidence(submissions),
    )

    delivery.deliver(
        "job-a",
        user_id="user-a",
        project_id="project-a",
        send=lambda _report: None,
    )

    with pytest.raises(ValueError, match="submitted SEPA"):
        invoices.build(
            "invoice-a",
            "payment-a",
            job_id="job-a",
            user_id="user-a",
            project_id="project-a",
        )

    provider_reference = sepa.submit(
        "payment-a",
        "mandate-a",
        user_id="user-a",
        project_id="project-a",
    )
    basis = invoices.build(
        "invoice-a",
        "payment-a",
        job_id="job-a",
        user_id="user-a",
        project_id="project-a",
    )

    assert provider_reference == "provider-debit-a"
    assert basis.payment_id == "payment-a"
    assert basis.job_id == "job-a"
    assert basis.amount == PaymentAmount(12900, "EUR")
    assert submissions.get("payment-a").status is SepaSubmissionStatus.SUBMITTED
    assert len(gateway.calls) == 1


def test_sepa_return_after_invoice_remains_persisted_payment_state(tmp_path) -> None:
    billing, payments, _gateway, submissions, collections, sepa, delivery = setup_flow(tmp_path)
    invoices = InvoiceBasisService(
        billing,
        payments,
        PaymentExecutionEvidence(submissions),
    )

    delivery.deliver(
        "job-a",
        user_id="user-a",
        project_id="project-a",
        send=lambda _report: None,
    )
    sepa.submit(
        "payment-a",
        "mandate-a",
        user_id="user-a",
        project_id="project-a",
    )
    basis = invoices.build(
        "invoice-a",
        "payment-a",
        job_id="job-a",
        user_id="user-a",
        project_id="project-a",
    )

    updates = SepaCollectionUpdateService(collections)
    updates.apply_verified_update(
        "provider-a", "provider-debit-a", SepaCollectionStatus.SUCCEEDED
    )
    returned = updates.apply_verified_update(
        "provider-a", "provider-debit-a", SepaCollectionStatus.RETURNED
    )

    assert basis.payment_id == "payment-a"
    assert returned.status is SepaCollectionStatus.RETURNED
    assert collections.get("sepa:payment-a").status is SepaCollectionStatus.RETURNED
    with pytest.raises(ValueError, match="cannot transition"):
        updates.apply_verified_update(
            "provider-a", "provider-debit-a", SepaCollectionStatus.SUCCEEDED
        )
