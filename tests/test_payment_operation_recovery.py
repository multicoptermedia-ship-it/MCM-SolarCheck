from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.sqlite_payment import SQLiteOnlinePaymentStore
from mcm_solarcheck.infrastructure.sqlite_payment_operation import (
    SQLitePaymentOperationIntentStore,
)
from mcm_solarcheck.services.billing import ComputeJobBilling, ComputeJobDelivery
from mcm_solarcheck.services.payment import OnlinePayment, PaymentAmount, PaymentStatus
from mcm_solarcheck.services.payment_methods import PaymentMethod
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


class FailOnceCompletionStore:
    def __init__(self, delegate):
        self.delegate = delegate
        self.failed = False

    def reserve(self, intent):
        return self.delegate.reserve(intent)

    def get(self, payment_id):
        return self.delegate.get(payment_id)

    def mark_provider_succeeded(self, payment_id):
        return self.delegate.mark_provider_succeeded(payment_id)

    def mark_completed(self, payment_id):
        if not self.failed:
            self.failed = True
            raise RuntimeError("simulated crash before intent completion")
        return self.delegate.mark_completed(payment_id)


def test_capture_retry_completes_intent_after_local_capture_crash_window(tmp_path) -> None:
    payments = authorized_payment_store(tmp_path)
    durable_intents = SQLitePaymentOperationIntentStore(tmp_path / "operations.sqlite")
    intents = FailOnceCompletionStore(durable_intents)
    gateway = RecordingGateway()
    service = PaymentCaptureService(payments, BillingStore(), gateway, intents)

    with pytest.raises(RuntimeError, match="intent completion"):
        service.capture("payment-a", user_id="user-a", project_id="project-a")

    assert payments.get("payment-a").status is PaymentStatus.CAPTURED
    assert durable_intents.get("payment-a").status is PaymentOperationStatus.PROVIDER_SUCCEEDED

    recovered = PaymentCaptureService(
        payments, BillingStore(), gateway, durable_intents
    ).capture("payment-a", user_id="user-a", project_id="project-a")

    assert recovered.status is PaymentStatus.CAPTURED
    assert len(gateway.captures) == 1
    assert durable_intents.get("payment-a").status is PaymentOperationStatus.COMPLETED


def test_void_retry_completes_intent_after_local_void_crash_window(tmp_path) -> None:
    payments = authorized_payment_store(tmp_path)
    durable_intents = SQLitePaymentOperationIntentStore(tmp_path / "operations.sqlite")
    intents = FailOnceCompletionStore(durable_intents)
    gateway = RecordingGateway()
    service = PaymentVoidService(payments, gateway, intents)

    with pytest.raises(RuntimeError, match="intent completion"):
        service.void("payment-a", user_id="user-a", project_id="project-a")

    assert payments.get("payment-a").status is PaymentStatus.VOIDED
    assert durable_intents.get("payment-a").status is PaymentOperationStatus.PROVIDER_SUCCEEDED

    recovered = PaymentVoidService(
        payments, gateway, durable_intents
    ).void("payment-a", user_id="user-a", project_id="project-a")

    assert recovered.status is PaymentStatus.VOIDED
    assert len(gateway.voids) == 1
    assert durable_intents.get("payment-a").status is PaymentOperationStatus.COMPLETED


class FailOnceProviderSuccessIntentStore:
    def __init__(self, delegate):
        self.delegate = delegate
        self.failed = False

    def reserve(self, intent):
        return self.delegate.reserve(intent)

    def get(self, payment_id):
        return self.delegate.get(payment_id)

    def mark_provider_succeeded(self, payment_id):
        if not self.failed:
            self.failed = True
            raise RuntimeError("simulated crash before provider success persistence")
        return self.delegate.mark_provider_succeeded(payment_id)

    def mark_completed(self, payment_id):
        return self.delegate.mark_completed(payment_id)


def test_capture_retry_reuses_idempotency_key_when_provider_success_was_not_persisted(tmp_path) -> None:
    payments = authorized_payment_store(tmp_path)
    durable_intents = SQLitePaymentOperationIntentStore(tmp_path / "operations.sqlite")
    intents = FailOnceProviderSuccessIntentStore(durable_intents)
    gateway = RecordingGateway()
    service = PaymentCaptureService(payments, BillingStore(), gateway, intents)

    with pytest.raises(RuntimeError, match="provider success persistence"):
        service.capture("payment-a", user_id="user-a", project_id="project-a")

    assert payments.get("payment-a").status is PaymentStatus.AUTHORIZED
    assert durable_intents.get("payment-a").status is PaymentOperationStatus.RESERVED

    captured = PaymentCaptureService(
        payments, BillingStore(), gateway, durable_intents
    ).capture("payment-a", user_id="user-a", project_id="project-a")

    assert captured.status is PaymentStatus.CAPTURED
    assert len(gateway.captures) == 2
    assert gateway.captures[0][1] == gateway.captures[1][1]
    assert gateway.captures[0][1] == "payment:payment-a:capture"
    assert durable_intents.get("payment-a").status is PaymentOperationStatus.COMPLETED


def test_void_retry_reuses_idempotency_key_when_provider_success_was_not_persisted(tmp_path) -> None:
    payments = authorized_payment_store(tmp_path)
    durable_intents = SQLitePaymentOperationIntentStore(tmp_path / "operations.sqlite")
    intents = FailOnceProviderSuccessIntentStore(durable_intents)
    gateway = RecordingGateway()
    service = PaymentVoidService(payments, gateway, intents)

    with pytest.raises(RuntimeError, match="provider success persistence"):
        service.void("payment-a", user_id="user-a", project_id="project-a")

    assert payments.get("payment-a").status is PaymentStatus.AUTHORIZED
    assert durable_intents.get("payment-a").status is PaymentOperationStatus.RESERVED

    voided = PaymentVoidService(
        payments, gateway, durable_intents
    ).void("payment-a", user_id="user-a", project_id="project-a")

    assert voided.status is PaymentStatus.VOIDED
    assert len(gateway.voids) == 2
    assert gateway.voids[0][1] == gateway.voids[1][1]
    assert gateway.voids[0][1] == "payment:payment-a:void"
    assert durable_intents.get("payment-a").status is PaymentOperationStatus.COMPLETED


@pytest.mark.parametrize("operation", ["capture", "void"])
def test_sepa_cannot_enter_card_like_terminal_operation(tmp_path, operation) -> None:
    payments = SQLiteOnlinePaymentStore(tmp_path / f"sepa-{operation}.sqlite")
    payments.create(
        OnlinePayment(
            "payment-sepa",
            "user-a",
            "project-a",
            "job-a",
            PaymentAmount(12900, "EUR"),
            method=PaymentMethod.SEPA_DIRECT_DEBIT,
        )
    )
    payments.authorize(
        "payment-sepa", "user-a", "project-a", "provider-auth-sepa"
    )
    intents = SQLitePaymentOperationIntentStore(
        tmp_path / f"sepa-{operation}-operations.sqlite"
    )
    gateway = RecordingGateway()

    if operation == "capture":
        service = PaymentCaptureService(payments, BillingStore(), gateway, intents)
        with pytest.raises(ValueError, match="does not support capture"):
            service.capture(
                "payment-sepa", user_id="user-a", project_id="project-a"
            )
    else:
        service = PaymentVoidService(payments, gateway, intents)
        with pytest.raises(ValueError, match="does not support void"):
            service.void(
                "payment-sepa", user_id="user-a", project_id="project-a"
            )

    assert payments.get("payment-sepa").status is PaymentStatus.AUTHORIZED
    assert gateway.captures == []
    assert gateway.voids == []
    with pytest.raises(KeyError):
        intents.get("payment-sepa")
