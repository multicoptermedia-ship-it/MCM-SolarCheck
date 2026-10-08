from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton

from mcm_solarcheck.gui.entry_page import make_entry_page
from mcm_solarcheck.services.deployment import DeploymentMode


def test_registration_success_is_visible_on_login_page() -> None:
    application = QApplication.instance() or QApplication([])
    page = make_entry_page(
        DeploymentMode.ONLINE,
        on_register=lambda request: "Bestätigungs-E-Mail wurde gesendet.",
    )

    page.findChild(QPushButton, "register_button").click()

    assert application is not None
    assert page.findChild(QLabel, "registration_status").text() == (
        "Bestätigungs-E-Mail wurde gesendet."
    )


def test_verification_failure_is_visible_without_gui_state_transition() -> None:
    application = QApplication.instance() or QApplication([])

    def reject(_token: str) -> str:
        raise ValueError("verification token is invalid")

    page = make_entry_page(
        DeploymentMode.ONLINE,
        on_email_verification=reject,
    )
    page.findChild(QLineEdit, "email_verification_token").setText("bad-token")
    page.findChild(QPushButton, "email_verification_button").click()

    assert application is not None
    assert page.findChild(QLabel, "registration_status").text() == (
        "verification token is invalid"
    )
