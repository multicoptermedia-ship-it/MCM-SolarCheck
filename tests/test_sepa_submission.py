from datetime import datetime, timedelta, timezone

from mcm_solarcheck.infrastructure.sqlite_payment import SQLiteOnlinePaymentStore
from mcm_solarcheck.infrastructure.sqlite_sepa import SQLiteSepaMandateStore
from mcm_solarcheck.infrastructure.sqlite_sepa_collection import (
    SQLiteSepaCollectionStore,
)
from mcm_solarcheck.infrastructure.sqlite_sepa_submission import (
    SQLiteSepaSubmissionStore,
)
from mcm_solarcheck.services.billing import ComputeJobBilling, ComputeJobDelivery
from mcm_solarcheck.services.payment import OnlinePayment, PaymentAmount
from mcm_solarcheck.services.payment_methods import PaymentMethod
from mcm_solarcheck.services.sepa import SepaMandate
from mcm_solarcheck.services.sepa_payment import SepaPaymentService
from mcm_solarcheck.services.sepa_submission import SepaSubmission, SepaSubmissionStatus

import pytest


class MemoryBillingStore:
    def get(self, job_id):
        if job_id != "job-a":
            raise KeyError(job_id)
        return ComputeJobBilling(
            ComputeJobDelivery(
                "job-a",
                "user-a",
                "project-a",
                export_completed=True,
                report_retrieved=True,
            ),
            billing_released=True,
        )


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

    def reserve(self, submission, *, now):
        return self.delegate.reserve(submission, now=now)

    def mark_submitted(self, payment_id, provider_reference, lease_token):
        if not self.failed:
            self.failed = True
            raise RuntimeError("simulated crash after provider success")
        return self.delegate.mark_submitted(
            payment_id, provider_reference, lease_token
        )

    def release(self, payment_id, lease_token):
        return self.delegate.release(payment_id, lease_token)


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
        billing=MemoryBillingStore(),
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


def test_reserved_sepa_intent_rejects_conflicting_retry(tmp_path) -> None:
    store = SQLiteSepaSubmissionStore(tmp_path / "submissions.sqlite")
    original = SepaSubmission(
        "payment-a",
        "mandate-a",
        "user-a",
        "project-a",
        "provider-a",
        "payment:payment-a:sepa-submit",
    )
    store.reserve(
        original,
        now=datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc),
    )

    conflicting = SepaSubmission(
        "payment-a",
        "mandate-b",
        "user-a",
        "project-a",
        "provider-a",
        "payment:payment-a:sepa-submit",
    )
    with pytest.raises(ValueError, match="conflicting"):
        store.reserve(
            conflicting,
            now=datetime(2026, 9, 29, 12, 1, tzinfo=timezone.utc),
        )


def test_submitted_sepa_intent_is_idempotent_for_same_reference(tmp_path) -> None:
    store = SQLiteSepaSubmissionStore(tmp_path / "submissions.sqlite")
    reserved = store.reserve(
        SepaSubmission(
            "payment-a",
            "mandate-a",
            "user-a",
            "project-a",
            "provider-a",
            "payment:payment-a:sepa-submit",
        ),
        now=datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc),
    )

    first = store.mark_submitted(
        "payment-a", "provider-debit-a", reserved.lease_token
    )
    second = store.mark_submitted(
        "payment-a", "provider-debit-a", "retry-token"
    )

    assert first == second
    assert second.status is SepaSubmissionStatus.SUBMITTED


def test_active_sepa_submission_lease_blocks_parallel_worker(tmp_path) -> None:
    store = SQLiteSepaSubmissionStore(
        tmp_path / "submissions.sqlite",
        lease_seconds=60,
    )
    intent = SepaSubmission(
        "payment-a",
        "mandate-a",
        "user-a",
        "project-a",
        "provider-a",
        "payment:payment-a:sepa-submit",
    )
    now = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    first = store.reserve(intent, now=now)

    with pytest.raises(RuntimeError, match="already being processed"):
        store.reserve(intent, now=now + timedelta(seconds=30))

    assert first.lease_token is not None


def test_expired_sepa_submission_lease_fences_stale_worker(tmp_path) -> None:
    store = SQLiteSepaSubmissionStore(
        tmp_path / "submissions.sqlite",
        lease_seconds=60,
    )
    intent = SepaSubmission(
        "payment-a",
        "mandate-a",
        "user-a",
        "project-a",
        "provider-a",
        "payment:payment-a:sepa-submit",
    )
    now = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    first = store.reserve(intent, now=now)
    reclaimed = store.reserve(intent, now=now + timedelta(seconds=61))

    assert reclaimed.lease_token != first.lease_token
    with pytest.raises(ValueError, match="ownership lost"):
        store.mark_submitted(
            "payment-a", "provider-debit-a", first.lease_token
        )

    submitted = store.mark_submitted(
        "payment-a", "provider-debit-a", reclaimed.lease_token
    )
    assert submitted.status is SepaSubmissionStatus.SUBMITTED


def test_submitted_sepa_reservation_returns_persisted_reference(tmp_path) -> None:
    store = SQLiteSepaSubmissionStore(tmp_path / "submissions.sqlite")
    intent = SepaSubmission(
        "payment-a",
        "mandate-a",
        "user-a",
        "project-a",
        "provider-a",
        "payment:payment-a:sepa-submit",
    )
    now = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    reserved = store.reserve(intent, now=now)
    store.mark_submitted(
        "payment-a", "provider-debit-a", reserved.lease_token
    )

    retry = store.reserve(intent, now=now + timedelta(seconds=1))

    assert retry.status is SepaSubmissionStatus.SUBMITTED
    assert retry.provider_reference == "provider-debit-a"


def test_pending_sepa_submission_requires_complete_lease_pair() -> None:
    kwargs = dict(
        payment_id="payment-a",
        mandate_id="mandate-a",
        user_id="user-a",
        project_id="project-a",
        provider_id="provider-a",
        idempotency_key="payment:payment-a:sepa-submit",
    )

    with pytest.raises(ValueError, match="set together"):
        SepaSubmission(**kwargs, lease_token="token-a")

    with pytest.raises(ValueError, match="set together"):
        SepaSubmission(
            **kwargs,
            lease_until="2026-09-30T08:01:00+00:00",
        )
