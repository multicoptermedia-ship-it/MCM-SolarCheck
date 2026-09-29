"""Authenticated provider webhook boundary for payment events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

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


class PaymentWebhookVerifier(Protocol):
    """Provider adapter authenticates and normalizes a raw webhook."""

    def verify(self, request: PaymentWebhookRequest) -> SepaProviderEvent:
        ...


class PaymentWebhookService:
    def __init__(
        self,
        verifiers: dict[str, PaymentWebhookVerifier],
        reconciliation: SepaReconciliationService,
    ) -> None:
        if not verifiers:
            raise ValueError("at least one payment webhook verifier is required")
        self._verifiers = dict(verifiers)
        self._reconciliation = reconciliation

    def handle(self, request: PaymentWebhookRequest) -> SepaCollection:
        try:
            verifier = self._verifiers[request.provider_id]
        except KeyError:
            raise PermissionError("unconfigured payment webhook provider") from None

        event = verifier.verify(request)
        if event.provider_id != request.provider_id:
            raise PermissionError("verified webhook provider mismatch")
        return self._reconciliation.apply(event)
