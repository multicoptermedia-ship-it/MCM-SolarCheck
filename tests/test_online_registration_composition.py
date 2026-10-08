from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton

from mcm_solarcheck.online.entrypoint import build_online_window
from mcm_solarcheck.online.product import OnlineProduct
from mcm_solarcheck.services.online_entitlement import OnlineProduct as EntitlementProduct


class Production:
    def require_active(self) -> None:
        raise RuntimeError("production inactive")


class Registration:
    def __init__(self) -> None:
        self.register_calls = []
        self.verify_calls = []

    def register(self, **kwargs) -> None:
        self.register_calls.append(kwargs)

    def verify_and_activate(self, token, *, product, now) -> None:
        self.verify_calls.append((token, product, now))


class Services:
    def __init__(self) -> None:
        self.production = Production()
        self.registration = Registration()


def test_online_window_automatically_wires_composed_registration_service() -> None:
    application = QApplication.instance() or QApplication([])
    services = Services()
    window = build_online_window(OnlineProduct.compose(services))

    values = {
        "registration_user_id": "user-1",
        "registration_display_name": "MCM Dronetech",
        "registration_email": "user@example.com",
        "registration_street": "Musterweg 1",
        "registration_postal_code": "50181",
        "registration_city": "Bedburg",
    }
    for object_name, value in values.items():
        window.findChild(QLineEdit, object_name).setText(value)

    window.findChild(QPushButton, "register_button").click()

    assert application is not None
    assert len(services.registration.register_calls) == 1
    call = services.registration.register_calls[0]
    assert {key: call[key] for key in values.values() if False} == {}
    assert call["user_id"] == "user-1"
    assert call["email"] == "user@example.com"
    assert call["now"].utcoffset().total_seconds() == 0


def test_online_window_verification_activates_fixed_trial_entitlement() -> None:
    application = QApplication.instance() or QApplication([])
    services = Services()
    window = build_online_window(OnlineProduct.compose(services))
    window.findChild(QLineEdit, "email_verification_token").setText("opaque-token")

    window.findChild(QPushButton, "email_verification_button").click()

    assert application is not None
    assert len(services.registration.verify_calls) == 1
    token, product, now = services.registration.verify_calls[0]
    assert token == "opaque-token"
    assert product is EntitlementProduct.TRIAL
    assert now.utcoffset().total_seconds() == 0
