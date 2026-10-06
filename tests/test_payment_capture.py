from __future__ import annotations

import pytest
from datetime import datetime, timezone

from mcm_solarcheck.infrastructure.sqlite_introductory_offer import SQLiteIntroductoryOfferStore

from mcm_solarcheck.services.billing import (
    ComputeJobBilling,
    ComputeJobDelivery,
)
from mcm_solarcheck.services.payment import (
    OnlinePayment,
    PaymentAmount,
    PaymentStatus,
)
from mcm_solarcheck.services.payment_capture import PaymentCaptureService


class MemoryPaymentStore:
    def __init__(self, payment: OnlinePayment) -> None:
        self.payment = payment

    def get(self, payment_id: str) -> OnlinePayment:
        if payment_id != self.payment.payment_id:
            raise KeyError(payment_id)
        return self.payment

    def capture(self, payment_id: str, user_id: str, project_id: str) -> OnlinePayment:
        payment = self.get(payment_id)
        if payment.user_id != user_id or payment.project_id != project_id:
            raise PermissionError("payment ownership mismatch")
        self.payment = payment.capture()
        return self.payment


class MemoryBillingStore:
    def __init__(self, billing: ComputeJobBilling) -> None:
        self.billing = billing

    def get(self, job_id: str) -> ComputeJobBilling:
        if job_id != self.billing.delivery.job_id:
            raise KeyError(job_id)
        return self.billing


def authorized_payment() -> OnlinePayment:
    return OnlinePayment(
        "payment-a",
        "user-a",
        "project-a",
        "job-a",
        PaymentAmount(12900, "EUR"),
    ).authorize("provider-auth-a")


def billing(
    *,
    released: bool,
    export_completed: bool = True,
    report_retrieved: bool = True,
) -> ComputeJobBilling:
    return ComputeJobBilling(
        ComputeJobDelivery(
            "job-a",
            "user-a",
            "project-a",
            export_completed=export_completed,
            report_retrieved=report_retrieved,
        ),
        billing_released=released,
    )


def test_capture_requires_server_released_delivered_result() -> None:
    payments = MemoryPaymentStore(authorized_payment())
    service = PaymentCaptureService(payments, MemoryBillingStore(billing(released=False)))

    with pytest.raises(ValueError, match="billing must be released"):
        service.capture("payment-a", user_id="user-a", project_id="project-a")

    assert payments.payment.status is PaymentStatus.AUTHORIZED


def test_capture_succeeds_after_billing_release() -> None:
    payments = MemoryPaymentStore(authorized_payment())
    service = PaymentCaptureService(payments, MemoryBillingStore(billing(released=True)))

    captured = service.capture(
        "payment-a", user_id="user-a", project_id="project-a"
    )

    assert captured.status is PaymentStatus.CAPTURED
    assert payments.payment == captured


def test_capture_rejects_cross_tenant_payment_access() -> None:
    payments = MemoryPaymentStore(authorized_payment())
    service = PaymentCaptureService(payments, MemoryBillingStore(billing(released=True)))

    with pytest.raises(PermissionError, match="ownership mismatch"):
        service.capture("payment-a", user_id="user-b", project_id="project-a")


def test_capture_rejects_billing_from_another_project() -> None:
    payments = MemoryPaymentStore(authorized_payment())
    foreign = ComputeJobBilling(
        ComputeJobDelivery(
            "job-a",
            "user-a",
            "project-b",
            export_completed=True,
            report_retrieved=True,
        ),
        billing_released=True,
    )
    service = PaymentCaptureService(payments, MemoryBillingStore(foreign))

    with pytest.raises(PermissionError, match="billing identity mismatch"):
        service.capture("payment-a", user_id="user-a", project_id="project-a")


@pytest.mark.parametrize(
    ("export_completed", "report_retrieved"),
    [
        (True, False),
    ],
)
def test_capture_requires_both_delivery_events(
    export_completed,
    report_retrieved,
) -> None:
    payments = MemoryPaymentStore(authorized_payment())
    service = PaymentCaptureService(
        payments,
        MemoryBillingStore(
            billing(
                released=False,
                export_completed=export_completed,
                report_retrieved=report_retrieved,
            )
        ),
    )

    with pytest.raises(ValueError, match="export and report retrieval"):
        service.capture(
            "payment-a",
            user_id="user-a",
            project_id="project-a",
        )

    assert payments.payment.status is PaymentStatus.AUTHORIZED


def test_capture_finalizes_reserved_introductory_offer(tmp_path) -> None:
    payments = MemoryPaymentStore(authorized_payment())
    offers = SQLiteIntroductoryOfferStore(tmp_path / "offers.sqlite")
    now = datetime(2026, 10, 6, tzinfo=timezone.utc)
    assert offers.reserve("user-a", "payment-a", policy_version=1, now=now)
    service = PaymentCaptureService(
        payments,
        MemoryBillingStore(billing(released=True)),
        introductory_offers=offers,
    )

    service.capture("payment-a", user_id="user-a", project_id="project-a")

    assert offers.has_used("user-a") is True
