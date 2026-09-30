from __future__ import annotations

import pytest
from datetime import datetime, timezone

from mcm_solarcheck.services.billing import ComputeJobBilling, ComputeJobDelivery
from mcm_solarcheck.services.invoice import InvoiceBasisService, invoice_customer_from_registration
from mcm_solarcheck.services.payment import OnlinePayment, PaymentAmount
from mcm_solarcheck.services.registration import OnlineRegistration, RegistrationStatus


class BillingStore:
    def __init__(self, value: ComputeJobBilling) -> None:
        self.value = value

    def get(self, job_id: str) -> ComputeJobBilling:
        if job_id != self.value.delivery.job_id:
            raise KeyError(job_id)
        return self.value


class PaymentStore:
    def __init__(self, value: OnlinePayment) -> None:
        self.value = value

    def get(self, payment_id: str) -> OnlinePayment:
        if payment_id != self.value.payment_id:
            raise KeyError(payment_id)
        return self.value


def billing(*, released: bool, retrieved: bool = True) -> ComputeJobBilling:
    return ComputeJobBilling(
        ComputeJobDelivery(
            "job-a", "user-a", "project-a",
            export_completed=True, report_retrieved=retrieved,
        ),
        billing_released=released,
    )


def payment(*, project_id: str = "project-a") -> OnlinePayment:
    return OnlinePayment(
        "payment-a", "user-a", project_id, "job-a",
        PaymentAmount(12900, "EUR"),
    )


def test_invoice_basis_uses_authoritative_payment_amount_after_release() -> None:
    service = InvoiceBasisService(
        BillingStore(billing(released=True)),
        PaymentStore(payment()),
    )

    basis = service.build(
        "invoice-a", "payment-a",
        job_id="job-a", user_id="user-a", project_id="project-a",
    )

    assert basis.amount == PaymentAmount(12900, "EUR")
    assert basis.payment_id == "payment-a"
    assert basis.job_id == "job-a"


def test_invoice_basis_blocked_before_billing_release() -> None:
    service = InvoiceBasisService(
        BillingStore(billing(released=False)),
        PaymentStore(payment()),
    )

    with pytest.raises(ValueError, match="billing release"):
        service.build(
            "invoice-a", "payment-a",
            job_id="job-a", user_id="user-a", project_id="project-a",
        )


def test_invoice_basis_rejects_payment_from_other_project() -> None:
    service = InvoiceBasisService(
        BillingStore(billing(released=True)),
        PaymentStore(payment(project_id="project-b")),
    )

    with pytest.raises(PermissionError, match="payment identity"):
        service.build(
            "invoice-a", "payment-a",
            job_id="job-a", user_id="user-a", project_id="project-a",
        )


def test_invoice_basis_blocked_without_report_delivery() -> None:
    service = InvoiceBasisService(
        BillingStore(billing(released=False, retrieved=False)),
        PaymentStore(payment()),
    )

    with pytest.raises(ValueError, match="report delivery"):
        service.build(
            "invoice-a", "payment-a",
            job_id="job-a", user_id="user-a", project_id="project-a",
        )


def test_invoice_customer_uses_verified_registration_billing_address() -> None:
    registration = OnlineRegistration(
        "user-a", "Testkunde GmbH", "kunde@example.com",
        RegistrationStatus.VERIFIED, datetime(2026, 9, 30, tzinfo=timezone.utc),
        "Musterweg 1", "50181", "Bedburg",
    )

    customer = invoice_customer_from_registration(registration)

    assert customer.name == "Testkunde GmbH"
    assert customer.address_lines == ("Musterweg 1", "50181 Bedburg")
    assert customer.email == "kunde@example.com"


def test_invoice_customer_rejects_unverified_registration() -> None:
    registration = OnlineRegistration(
        "user-a", "Testkunde GmbH", "kunde@example.com",
        street="Musterweg 1", postal_code="50181", city="Bedburg",
    )

    with pytest.raises(ValueError, match="verified registration"):
        invoice_customer_from_registration(registration)


def test_legacy_verified_registration_without_address_cannot_be_invoiced() -> None:
    registration = OnlineRegistration(
        "user-a", "Altbestand", "alt@example.com",
        RegistrationStatus.VERIFIED, datetime(2026, 9, 30, tzinfo=timezone.utc),
    )

    with pytest.raises(ValueError, match="complete billing address"):
        invoice_customer_from_registration(registration)
