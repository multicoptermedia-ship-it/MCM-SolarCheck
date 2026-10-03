from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from mcm_solarcheck.services.online_entitlement import OnlineProduct
from mcm_solarcheck.services.online_registration_controller import RegistrationRequest
from mcm_solarcheck.services.online_registration_ui import RegistrationServiceController


@dataclass
class Entitlement:
    user_id: str


class RegistrationService:
    def register(self, **kwargs):
        return None

    def verify_and_activate(self, token, *, product, now):
        assert token == "opaque-token"
        assert product is OnlineProduct.TRIAL
        return Entitlement("user-1")


def test_controller_exposes_identity_only_after_successful_verification() -> None:
    controller = RegistrationServiceController(
        RegistrationService(),
        product=OnlineProduct.TRIAL,
        now=lambda: datetime(2026, 10, 3, tzinfo=timezone.utc),
    )

    assert controller.verified_user_id is None

    controller.verify_email_token("opaque-token")

    assert controller.verified_user_id == "user-1"
