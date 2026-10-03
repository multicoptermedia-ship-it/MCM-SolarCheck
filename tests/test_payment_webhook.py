import sqlite3
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pytest

from mcm_solarcheck.infrastructure.sqlite_payment_webhook import (
    SQLitePaymentWebhookReplayStore,
)
from mcm_solarcheck.infrastructure.sqlite_sepa_collection import (
    SQLiteSepaCollectionStore,
)
from mcm_solarcheck.payment_webhook_contracts import (
    WebhookReplayReservation,
    WebhookReplayStatus,
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


def test_webhook_event_id_rejects_changed_verified_payload(tmp_path) -> None:
    verifier = RecordingVerifier()
    store, _ = setup_service(tmp_path, verifier)
    replay = SQLitePaymentWebhookReplayStore(tmp_path / "replay.sqlite")
    service = PaymentWebhookService(
        {"provider-a": verifier},
        SepaReconciliationService(store),
        replay,
    )
    service.handle(request())

    changed = PaymentWebhookRequest(
        "provider-a",
        b'{"event":"payment.changed"}',
        "signed-value",
    )
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        service.handle(changed)


def test_expired_webhook_lease_can_be_reclaimed_after_crash(tmp_path) -> None:
    replay = SQLitePaymentWebhookReplayStore(
        tmp_path / "replay.sqlite",
        lease_seconds=60,
    )
    now = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    fingerprint = sha256(b"verified-payload").hexdigest()

    first = replay.reserve(
        "provider-a", "event-crash", fingerprint, now=now
    )
    active = replay.reserve(
        "provider-a",
        "event-crash",
        fingerprint,
        now=now + timedelta(seconds=30),
    )
    reclaimed = replay.reserve(
        "provider-a",
        "event-crash",
        fingerprint,
        now=now + timedelta(seconds=61),
    )

    assert first.status is WebhookReplayStatus.ACQUIRED
    assert active.status is WebhookReplayStatus.PROCESSING
    assert reclaimed.status is WebhookReplayStatus.ACQUIRED
    assert reclaimed.lease_token != first.lease_token

    with pytest.raises(ValueError, match="ownership lost"):
        replay.mark_processed(
            "provider-a", "event-crash", first.lease_token
        )
    with pytest.raises(ValueError, match="ownership lost"):
        replay.release(
            "provider-a", "event-crash", first.lease_token
        )

    replay.mark_processed(
        "provider-a", "event-crash", reclaimed.lease_token
    )
    assert replay.is_processed("provider-a", "event-crash")


def test_active_webhook_lease_reports_processing_instead_of_stale_success(tmp_path) -> None:
    verifier = RecordingVerifier()
    store, _ = setup_service(tmp_path, verifier)
    replay = SQLitePaymentWebhookReplayStore(
        tmp_path / "replay-processing.sqlite",
        lease_seconds=60,
    )
    fingerprint = sha256(request().payload).hexdigest()
    reservation = replay.reserve(
        "provider-a",
        "event-a",
        fingerprint,
        now=datetime.now(timezone.utc),
    )
    assert reservation.status is WebhookReplayStatus.ACQUIRED

    service = PaymentWebhookService(
        {"provider-a": verifier},
        SepaReconciliationService(store),
        replay,
    )
    with pytest.raises(RuntimeError, match="already being processed"):
        service.handle(request())

    assert store.get("collection-a").status is SepaCollectionStatus.SUBMITTED


class MarkFailsReplay:
    def __init__(self) -> None:
        self.released = False

    def reserve(self, provider_id, event_id, fingerprint, *, now):
        return WebhookReplayReservation(WebhookReplayStatus.ACQUIRED, "lease-a")

    def mark_processed(self, provider_id, event_id, lease_token):
        raise ValueError("webhook replay lease ownership lost")

    def release(self, provider_id, event_id, lease_token):
        self.released = True


def test_successful_reconciliation_does_not_release_lost_webhook_lease(tmp_path) -> None:
    verifier = RecordingVerifier()
    store, _ = setup_service(tmp_path, verifier)
    replay = MarkFailsReplay()
    service = PaymentWebhookService(
        {"provider-a": verifier},
        SepaReconciliationService(store),
        replay,
    )

    with pytest.raises(ValueError, match="ownership lost"):
        service.handle(request())

    assert store.get("collection-a").status is SepaCollectionStatus.SUCCEEDED
    assert replay.released is False


def test_webhook_replay_contract_rejects_invalid_token_state() -> None:
    with pytest.raises(ValueError, match="requires token"):
        WebhookReplayReservation(WebhookReplayStatus.ACQUIRED)

    with pytest.raises(ValueError, match="cannot carry token"):
        WebhookReplayReservation(WebhookReplayStatus.PROCESSED, "stale-token")


def test_legacy_pending_webhook_row_is_migrated_and_reclaimed(tmp_path) -> None:
    database = tmp_path / "legacy-replay.sqlite"
    connection = sqlite3.connect(database)
    connection.execute(
        """
        CREATE TABLE payment_webhook_events (
            provider_id TEXT NOT NULL,
            event_id TEXT NOT NULL,
            processed INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (provider_id, event_id)
        )
        """
    )
    connection.execute(
        """
        INSERT INTO payment_webhook_events (provider_id, event_id, processed)
        VALUES (?, ?, 0)
        """,
        ("provider-a", "event-legacy"),
    )
    connection.commit()
    connection.close()

    replay = SQLitePaymentWebhookReplayStore(database, lease_seconds=60)
    now = datetime(2026, 9, 30, 8, 0, tzinfo=timezone.utc)
    fingerprint = sha256(b"legacy-verified-payload").hexdigest()

    reservation = replay.reserve(
        "provider-a",
        "event-legacy",
        fingerprint,
        now=now,
    )

    assert reservation.status is WebhookReplayStatus.ACQUIRED
    assert reservation.lease_token is not None
    replay.mark_processed(
        "provider-a",
        "event-legacy",
        reservation.lease_token,
    )
    assert replay.is_processed("provider-a", "event-legacy")


def test_legacy_processed_webhook_row_remains_processed_after_migration(tmp_path) -> None:
    database = tmp_path / "legacy-processed-replay.sqlite"
    connection = sqlite3.connect(database)
    connection.execute(
        """
        CREATE TABLE payment_webhook_events (
            provider_id TEXT NOT NULL,
            event_id TEXT NOT NULL,
            processed INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (provider_id, event_id)
        )
        """
    )
    connection.execute(
        """
        INSERT INTO payment_webhook_events (provider_id, event_id, processed)
        VALUES (?, ?, 1)
        """,
        ("provider-a", "event-legacy"),
    )
    connection.commit()
    connection.close()

    replay = SQLitePaymentWebhookReplayStore(database)
    reservation = replay.reserve(
        "provider-a",
        "event-legacy",
        sha256(b"legacy-verified-payload").hexdigest(),
        now=datetime(2026, 9, 30, 8, 0, tzinfo=timezone.utc),
    )

    assert reservation.status is WebhookReplayStatus.PROCESSED
    assert reservation.lease_token is None
