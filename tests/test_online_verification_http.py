from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from mcm_solarcheck.services.online_entitlement import OnlineProduct
from mcm_solarcheck.services.online_verification_http import EmailVerificationEndpoint


@dataclass
class Entitlement:
    user_id: str


class Registration:
    def __init__(self, error=None) -> None:
        self.calls = []
        self.error = error

    def verify_and_activate(self, token, *, product, now):
        self.calls.append((token, product, now))
        if self.error is not None:
            raise self.error
        return Entitlement("user-1")


def test_http_verification_delegates_to_authoritative_service() -> None:
    now = datetime(2026, 10, 3, 18, 0, tzinfo=timezone.utc)
    registration = Registration()
    endpoint = EmailVerificationEndpoint(registration, now=lambda: now)

    result = endpoint.verify("opaque-token")

    assert result.status_code == 200
    assert result.user_id == "user-1"
    assert registration.calls == [("opaque-token", OnlineProduct.TRIAL, now)]


def test_http_verification_rejects_missing_token_without_service_call() -> None:
    registration = Registration()
    endpoint = EmailVerificationEndpoint(registration)

    result = endpoint.verify("  ")

    assert result.status_code == 400
    assert result.user_id is None
    assert registration.calls == []


def test_http_verification_maps_invalid_or_expired_token_fail_closed() -> None:
    registration = Registration(ValueError("verification token is invalid"))
    endpoint = EmailVerificationEndpoint(registration)

    result = endpoint.verify("bad-token")

    assert result.status_code == 400
    assert result.user_id is None
    assert "invalid or expired" in result.message
