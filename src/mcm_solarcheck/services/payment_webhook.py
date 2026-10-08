"""Authenticated provider webhook boundary for payment events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Protocol

from mcm_solarcheck.payment_webhook_contracts import (
    WebhookReplayReservation,
    WebhookReplayStatus,
)
from mcm_solarcheck.services.sepa_collection import SepaCollection
from mcm_solarcheck.services.sepa_reconciliation import (
    SepaProviderEvent,
    SepaReconciliationService,
)


@dataclass(frozen=True)
class PaymentWebhookRequest:
    provider_id: str
    payload: bytes
    signature: str

    def __post_init__(self) -> None:
        if not isinstance(self.provider_id, str) or not self.provider_id.strip():
            raise ValueError("provider_id must be non-empty")
        if not isinstance(self.payload, bytes) or not self.payload:
            raise ValueError("webhook payload must be non-empty bytes")
        if not isinstance(self.signature, str) or not self.signature.strip():
            raise ValueError("webhook signature must be non-empty")


class PaymentWebhookReplayStore(Protocol):
    def reserve(
        self, provider_id: str, event_id: str, fingerprint: str, *, now: datetime
    ) -> WebhookReplayReservation:
        ...

    def mark_processed(
        self, provider_id: str, event_id: str, lease_token: str
    ) -> None:
        ...

    def release(
        self, provider_id: str, event_id: str, lease_token: str
    ) -> None:
        ...


class PaymentWebhookVerifier(Protocol):
    """Provider adapter authenticates and normalizes a raw webhook."""

    def verify(self, request: PaymentWebhookRequest) -> SepaProviderEvent:
        ...


class PaymentWebhookService:
    def __init__(
        self,
        verifiers: dict[str, PaymentWebhookVerifier],
        reconciliation: SepaReconciliationService,
        replay: PaymentWebhookReplayStore | None = None,
    ) -> None:
        if not verifiers:
            raise ValueError("at least one payment webhook verifier is required")
        self._verifiers = dict(verifiers)
        self._reconciliation = reconciliation
        self._replay = replay

    def handle(self, request: PaymentWebhookRequest) -> SepaCollection:
        try:
            verifier = self._verifiers[request.provider_id]
        except KeyError:
            raise PermissionError("unconfigured payment webhook provider") from None

        event = verifier.verify(request)
        if event.provider_id != request.provider_id:
            raise PermissionError("verified webhook provider mismatch")
        if self._replay is None or event.event_id is None:
            return self._reconciliation.apply(event)

        fingerprint = sha256(request.payload).hexdigest()
        reservation = self._replay.reserve(
            event.provider_id,
            event.event_id,
            fingerprint,
            now=datetime.now(timezone.utc),
        )
        if reservation.status is WebhookReplayStatus.PROCESSED:
            return self._reconciliation.resolve(
                event.provider_id, event.provider_reference
            )
        if reservation.status is WebhookReplayStatus.PROCESSING:
            raise RuntimeError("webhook event is already being processed")
        if reservation.lease_token is None:
            raise RuntimeError("acquired webhook replay lease has no token")

        try:
            result = self._reconciliation.apply(event)
        except Exception:
            try:
                self._replay.release(
                    event.provider_id,
                    event.event_id,
                    reservation.lease_token,
                )
            except ValueError:
                pass
            raise

        self._replay.mark_processed(
            event.provider_id,
            event.event_id,
            reservation.lease_token,
        )
        return result
