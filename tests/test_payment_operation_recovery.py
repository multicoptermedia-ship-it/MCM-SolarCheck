from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.sqlite_payment import SQLiteOnlinePaymentStore
from mcm_solarcheck.infrastructure.sqlite_payment_operation import (
    SQLitePaymentOperationIntentStore,
)
from mcm_solarcheck.services.billing import ComputeJobBilling, ComputeJobDelivery
from mcm_solarcheck.services.payment import OnlinePayment, PaymentAmount, PaymentStatus
from mcm_solarcheck.services.payment_capture import PaymentCaptureService
from mcm_solarcheck.services.payment_operation import PaymentOperationStatus
from mcm_solarcheck.services.payment_void import PaymentVoidService


class BillingStore:
    def get(self, job_id):
        return ComputeJobBilling(
            ComputeJobDelivery(
                job_id,
                "user-a",
                "project-a",
                export_completed=True,
                report_retrieved=True,
            ),
            billing_released=True,
        )


class RecordingGateway:
    def __init__(self):
        self.captures = []
        self.voids = []

    def capture(self, provider_reference, *, idempotency_key):
        self.captures.append((provider_reference, idempotency_key))

    def void(self, provider_reference, *, idempotency_key):
        self.voids.append((provider_reference, idempotency_key))


class FailOncePaymentStore:
    def __init__(self, delegate, operation):
        self.delegate = delegate
        self.operation = operation
        self.failed = False

    def get(self, payment_id):
        return self.delegate.get(payment_id)

    def capture(self, payment_id, user_id, project_id):
        if self.operation == "capture" and not self.failed:
            self.failed = True
            raise RuntimeError("simulated crash after provider success")
        return self.delegate.capture(payment_id, user_id, project_id)

    def void(self, payment_id, user_id, project_id):
        if self.operation == "void" and not self.failed:
            self.failed = True
            raise RuntimeError("simulated crash after provider success")
        return self.delegate.void(payment_id, user_id, project_id)


def authorized_payment_store(tmp_path):
    store = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    store.create(
        OnlinePayment(
            "payment-a",
            "user-a",
            "project-a",
            "job-a",
            PaymentAmount(12900, "EUR"),
        )
    )
    store.authorize(
        "payment-a",
        "user-a",
        "project-a",
        "provider-auth-a",
    )
    return store


def test_capture_retry_after_local_crash_does_not_call_provider_twice(tmp_path) -> None:
    payments = authorized_payment_store(tmp_path)
    intents = SQLitePaymentOperationIntentStore(tmp_path / "operations.sqlite")
    gateway = RecordingGateway()
    failing = FailOncePaymentStore(payments, "capture")
    service = PaymentCaptureService(failing, BillingStore(), gateway, intents)

    with pytest.raises(RuntimeError, match="simulated crash"):
        service.capture("payment-a", user_id="user-a", project_id="project-a")

    assert intents.get("payment-a").status is PaymentOperationStatus.PROVIDER_SUCCEEDED
    assert payments.get("payment-a").status is PaymentStatus.AUTHORIZED

    captured = PaymentCaptureService(
        payments, BillingStore(), gateway, intents
    ).capture("payment-a", user_id="user-a", project_id="project-a")

    assert captured.status is PaymentStatus.CAPTURED
    assert len(gateway.captures) == 1
    assert intents.get("payment-a").status is PaymentOperationStatus.COMPLETED


def test_void_retry_after_local_crash_does_not_call_provider_twice(tmp_path) -> None:
    payments = authorized_payment_store(tmp_path)
    intents = SQLitePaymentOperationIntentStore(tmp_path / "operations.sqlite")
    gateway = RecordingGateway()
    failing = FailOncePaymentStore(payments, "void")
    service = PaymentVoidService(failing, gateway, intents)

    with pytest.raises(RuntimeError, match="simulated crash"):
        service.void("payment-a", user_id="user-a", project_id="project-a")

    assert intents.get("payment-a").status is PaymentOperationStatus.PROVIDER_SUCCEEDED
    assert payments.get("payment-a").status is PaymentStatus.AUTHORIZED

    voided = PaymentVoidService(payments, gateway, intents).void(
        "payment-a", user_id="user-a", project_id="project-a"
    )

    assert voided.status is PaymentStatus.VOIDED
    assert len(gateway.voids) == 1
    assert intents.get("payment-a").status is PaymentOperationStatus.COMPLETED
