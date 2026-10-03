from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mcm_solarcheck.services.online_entitlement import OnlineProduct
from mcm_solarcheck.services.online_registration_controller import RegistrationRequest
from mcm_solarcheck.services.online_registration_ui import RegistrationServiceController


class RegistrationService:
    def __init__(self) -> None:
        self.register_calls = []
        self.verify_calls = []

    def register(self, **kwargs) -> None:
        self.register_calls.append(kwargs)

    def verify_and_activate(self, token, *, product, now) -> None:
        self.verify_calls.append((token, product, now))


def test_registration_controller_delegates_fields_with_utc_time() -> None:
    service = RegistrationService()
    now = datetime(2026, 10, 3, 14, 0, tzinfo=timezone.utc)
    controller = RegistrationServiceController(
        service,
        product=OnlineProduct.TRIAL,
        now=lambda: now,
    )

    controller.register(
        RegistrationRequest(
            user_id="user-1",
            display_name="MCM Dronetech",
            email="user@example.com",
            street="Musterweg 1",
            postal_code="50181",
            city="Bedburg",
        )
    )

    assert service.register_calls == [{
        "user_id": "user-1",
        "display_name": "MCM Dronetech",
        "email": "user@example.com",
        "street": "Musterweg 1",
        "postal_code": "50181",
        "city": "Bedburg",
        "now": now,
    }]


def test_verification_controller_delegates_token_and_fixed_product() -> None:
    service = RegistrationService()
    now = datetime(2026, 10, 3, 14, 1, tzinfo=timezone.utc)
    controller = RegistrationServiceController(
        service,
        product=OnlineProduct.TRIAL,
        now=lambda: now,
    )

    controller.verify_email_token("opaque-token")

    assert service.verify_calls == [("opaque-token", OnlineProduct.TRIAL, now)]


def test_registration_controller_rejects_non_utc_clock() -> None:
    service = RegistrationService()
    controller = RegistrationServiceController(
        service,
        product=OnlineProduct.TRIAL,
        now=lambda: datetime(2026, 10, 3, 14, 0),
    )

    with pytest.raises(ValueError, match="timezone-aware UTC"):
        controller.verify_email_token("opaque-token")
