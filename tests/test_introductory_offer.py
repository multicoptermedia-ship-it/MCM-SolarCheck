from datetime import datetime, timezone

import pytest

from mcm_solarcheck.services.payment import PaymentAmount
from mcm_solarcheck.services.introductory_offer import IntroductoryOfferPolicy


def test_introductory_offer_is_fixed_at_59_eur() -> None:
    policy = IntroductoryOfferPolicy()
    assert policy.amount == PaymentAmount(5900, "EUR")
    assert policy.version == 1


def test_introductory_offer_is_valid_through_2026_12_31() -> None:
    policy = IntroductoryOfferPolicy()
    assert policy.is_available_at(datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc))
    assert not policy.is_available_at(datetime(2027, 1, 1, 0, 0, tzinfo=timezone.utc))


def test_introductory_offer_requires_timezone_aware_evaluation() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        IntroductoryOfferPolicy().is_available_at(datetime(2026, 12, 31, 12, 0))


def test_verified_registration_is_required_for_offer() -> None:
    from mcm_solarcheck.services.introductory_offer import has_verified_registration
    from mcm_solarcheck.services.registration import OnlineRegistration

    class Registrations:
        def __init__(self, registration):
            self.registration = registration
        def get(self, user_id):
            if self.registration is None:
                raise KeyError(user_id)
            return self.registration

    pending = OnlineRegistration("user-a", "Customer", "customer@example.com")
    verified = pending.verify(datetime(2026, 10, 6, tzinfo=timezone.utc))

    assert has_verified_registration(Registrations(None), "user-a") is False
    assert has_verified_registration(Registrations(pending), "user-a") is False
    assert has_verified_registration(Registrations(verified), "user-a") is True
