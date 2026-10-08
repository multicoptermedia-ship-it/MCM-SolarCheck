from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton

from mcm_solarcheck.online.entrypoint import build_online_window
from mcm_solarcheck.online.product import OnlineProduct
from mcm_solarcheck.services.online_registration_controller import RegistrationRequest


class Production:
    def require_active(self) -> None:
        raise RuntimeError("production inactive")


class Services:
    production = Production()


class RegistrationController:
    def __init__(self) -> None:
        self.registrations = []
        self.tokens = []

    def register(self, request: RegistrationRequest) -> None:
        self.registrations.append(request)

    def verify_email_token(self, token: str) -> None:
        self.tokens.append(token)


def test_online_entry_routes_registration_fields_through_controller() -> None:
    application = QApplication.instance() or QApplication([])
    controller = RegistrationController()
    window = build_online_window(
        OnlineProduct.compose(Services()),
        registration_controller=controller,
    )

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
    assert controller.registrations == [
        RegistrationRequest(
            user_id="user-1",
            display_name="MCM Dronetech",
            email="user@example.com",
            street="Musterweg 1",
            postal_code="50181",
            city="Bedburg",
        )
    ]


def test_online_entry_routes_verification_token_without_interpreting_it() -> None:
    application = QApplication.instance() or QApplication([])
    controller = RegistrationController()
    window = build_online_window(
        OnlineProduct.compose(Services()),
        registration_controller=controller,
    )
    token = window.findChild(QLineEdit, "email_verification_token")
    token.setText("opaque-one-time-token")

    window.findChild(QPushButton, "email_verification_button").click()

    assert application is not None
    assert controller.tokens == ["opaque-one-time-token"]
