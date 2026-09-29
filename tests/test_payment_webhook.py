import pytest

from mcm_solarcheck.infrastructure.sqlite_payment_webhook import (
    SQLitePaymentWebhookReplayStore,
)
from mcm_solarcheck.infrastructure.sqlite_sepa_collection import (
    SQLiteSepaCollectionStore,
)
from mcm_solarcheck.services.payment_webhook import (
    PaymentWebhookRequest,
    PaymentWebhookService,
)
from mcm_solarcheck.services.sepa_collection import (
    SepaCollection,
    SepaCollectionStatus,
)
from mcm_solarcheck.services.sepa_reconciliation import (
    SepaProviderEvent,
    SepaReconciliationService,
)


class RecordingVerifier:
    def __init__(self, *, valid=True, provider_id="provider-a") -> None:
        self.valid = valid
        self.provider_id = provider_id
        self.requests = []

    def verify(self, request):
        self.requests.append(request)
        if not self.valid:
            raise PermissionError("invalid webhook signature")
        return SepaProviderEvent(
            self.provider_id,
            "provider-debit-a",
            SepaCollectionStatus.SUCCEEDED,
            "event-a",
        )


def setup_service(tmp_path, verifier):
    store = SQLiteSepaCollectionStore(tmp_path / "collections.sqlite")
    store.create(
        SepaCollection(
            "collection-a",
            "payment-a",
            "user-a",
            "project-a",
            "provider-a",
            "provider-debit-a",
        )
    )
    service = PaymentWebhookService(
        {"provider-a": verifier},
        SepaReconciliationService(store),
    )
    return store, service


def request(provider_id="provider-a"):
    return PaymentWebhookRequest(
        provider_id,
        b'{"event":"payment.updated"}',
        "signed-value",
    )


def test_verified_webhook_can_reconcile_payment(tmp_path) -> None:
    verifier = RecordingVerifier()
    store, service = setup_service(tmp_path, verifier)

    result = service.handle(request())

    assert result.status is SepaCollectionStatus.SUCCEEDED
    assert len(verifier.requests) == 1
    assert store.get("collection-a").status is SepaCollectionStatus.SUCCEEDED


def test_invalid_signature_cannot_mutate_payment(tmp_path) -> None:
    verifier = RecordingVerifier(valid=False)
    store, service = setup_service(tmp_path, verifier)

    with pytest.raises(PermissionError, match="signature"):
        service.handle(request())

    assert store.get("collection-a").status is SepaCollectionStatus.SUBMITTED


def test_unconfigured_provider_is_rejected_before_verification(tmp_path) -> None:
    verifier = RecordingVerifier()
    store, service = setup_service(tmp_path, verifier)

    with pytest.raises(PermissionError, match="unconfigured"):
        service.handle(request("provider-b"))

    assert verifier.requests == []
    assert store.get("collection-a").status is SepaCollectionStatus.SUBMITTED


def test_verifier_cannot_switch_provider_identity(tmp_path) -> None:
    verifier = RecordingVerifier(provider_id="provider-b")
    store, service = setup_service(tmp_path, verifier)

    with pytest.raises(PermissionError, match="provider mismatch"):
        service.handle(request())

    assert store.get("collection-a").status is SepaCollectionStatus.SUBMITTED


def test_authenticated_webhook_replay_is_processed_once(tmp_path) -> None:
    verifier = RecordingVerifier()
    store, _ = setup_service(tmp_path, verifier)
    replay = SQLitePaymentWebhookReplayStore(tmp_path / "replay.sqlite")
    service = PaymentWebhookService(
        {"provider-a": verifier},
        SepaReconciliationService(store),
        replay,
    )

    first = service.handle(request())
    second = service.handle(request())

    assert first == second
    assert replay.is_processed("provider-a", "event-a")
    assert store.get("collection-a").status is SepaCollectionStatus.SUCCEEDED


class FailOnceReconciliation:
    def __init__(self, delegate) -> None:
        self.delegate = delegate
        self.failed = False

    def apply(self, event):
        if not self.failed:
            self.failed = True
            raise RuntimeError("temporary reconciliation failure")
        return self.delegate.apply(event)

    def resolve(self, provider_id, provider_reference):
        return self.delegate.resolve(provider_id, provider_reference)


def test_failed_webhook_processing_can_be_retried(tmp_path) -> None:
    verifier = RecordingVerifier()
    store, _ = setup_service(tmp_path, verifier)
    replay = SQLitePaymentWebhookReplayStore(tmp_path / "replay.sqlite")
    reconciliation = FailOnceReconciliation(SepaReconciliationService(store))
    service = PaymentWebhookService(
        {"provider-a": verifier},
        reconciliation,
        replay,
    )

    with pytest.raises(RuntimeError, match="temporary"):
        service.handle(request())

    assert not replay.is_processed("provider-a", "event-a")

    result = service.handle(request())
    assert result.status is SepaCollectionStatus.SUCCEEDED
    assert replay.is_processed("provider-a", "event-a")
