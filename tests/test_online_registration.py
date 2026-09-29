from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from mcm_solarcheck.services.registration import (
    EmailVerification,
    OnlineRegistration,
    RegistrationStatus,
)


def test_online_registration_requires_name_and_plausible_email() -> None:
    with pytest.raises(ValueError):
        OnlineRegistration("user-a", " ", "user@example.com")
    with pytest.raises(ValueError):
        OnlineRegistration("user-a", "MCM Dronetech", "invalid")
    with pytest.raises(ValueError):
        OnlineRegistration("user-a", "MCM Dronetech", "user@localhost")


def test_online_registration_normalizes_email() -> None:
    registration = OnlineRegistration(
        "user-a",
        "MCM Dronetech",
        "  User@Example.COM  ",
    )
    assert registration.email == "user@example.com"
    assert registration.status is RegistrationStatus.PENDING


def test_registration_becomes_verified_only_with_explicit_utc_time() -> None:
    registration = OnlineRegistration(
        "user-a", "MCM Dronetech", "user@example.com"
    )
    now = datetime(2026, 9, 29, 8, 0, tzinfo=timezone.utc)
    verified = registration.verify(now)
    assert verified.status is RegistrationStatus.VERIFIED
    assert verified.verified_at == now
    assert verified.verify(now + timedelta(minutes=1)) == verified


def test_email_verification_has_explicit_expiry() -> None:
    start = datetime(2026, 9, 29, 8, 0, tzinfo=timezone.utc)
    verification = EmailVerification(
        "opaque-token", start, timedelta(minutes=30)
    )
    assert verification.valid_at(start + timedelta(minutes=29))
    assert not verification.valid_at(start + timedelta(minutes=30))
