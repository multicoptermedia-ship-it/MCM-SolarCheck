from __future__ import annotations

import pytest

from mcm_solarcheck.services.online_authentication import OnlineAuthenticationService
from mcm_solarcheck.services.registration import OnlineRegistration, RegistrationStatus
from datetime import datetime, timezone


class Registrations:
    def __init__(self, values):
        self.values = values

    def get(self, user_id):
        if user_id not in self.values:
            raise KeyError(user_id)
        return self.values[user_id]


def test_authentication_boundary_accepts_verified_identity() -> None:
    verified = OnlineRegistration(
        "user-1",
        "MCM Test",
        "user@example.com",
        RegistrationStatus.VERIFIED,
        datetime(2026, 10, 3, 18, 0, tzinfo=timezone.utc),
    )
    service = OnlineAuthenticationService(Registrations({"user-1": verified}))

    assert service.require_verified_identity("user-1") == "user-1"


def test_authentication_boundary_rejects_pending_identity() -> None:
    pending = OnlineRegistration("user-1", "MCM Test", "user@example.com")
    service = OnlineAuthenticationService(Registrations({"user-1": pending}))

    with pytest.raises(PermissionError, match="not verified"):
        service.require_verified_identity("user-1")


def test_authentication_boundary_rejects_unknown_identity() -> None:
    service = OnlineAuthenticationService(Registrations({}))

    with pytest.raises(PermissionError, match="not registered"):
        service.require_verified_identity("missing")


def test_authentication_boundary_rejects_blank_identity() -> None:
    service = OnlineAuthenticationService(Registrations({}))

    with pytest.raises(ValueError, match="non-empty"):
        service.require_verified_identity(" ")
