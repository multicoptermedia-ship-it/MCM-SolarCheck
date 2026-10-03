from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton

from mcm_solarcheck.gui.shell import SolarCheckMainWindow
from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.shell_navigation import ShellRoute


class CustomerEntry:
    def __init__(self) -> None:
        self.users = []

    def require_customer_entry(self, user_id=None) -> None:
        if user_id != "user-1":
            raise PermissionError("active entitlement required")
        self.users.append(user_id)


def test_successful_verification_enters_project_with_verified_identity() -> None:
    application = QApplication.instance() or QApplication([])
    entry = CustomerEntry()
    window = SolarCheckMainWindow(
        DeploymentMode.ONLINE,
        customer_entry=entry,
        on_email_verification=lambda token: (
            "E-Mail-Adresse wurde bestätigt.",
            "user-1",
        ),
    )
    window.findChild(QLineEdit, "email_verification_token").setText("opaque-token")

    window.findChild(QPushButton, "email_verification_button").click()

    assert application is not None
    assert entry.users == ["user-1"]
    assert window.current_route is ShellRoute.PROJECT


def test_failed_customer_entry_stays_on_login() -> None:
    application = QApplication.instance() or QApplication([])
    entry = CustomerEntry()
    window = SolarCheckMainWindow(
        DeploymentMode.ONLINE,
        customer_entry=entry,
        on_email_verification=lambda token: (
            "E-Mail-Adresse wurde bestätigt.",
            "wrong-user",
        ),
    )

    window.findChild(QPushButton, "email_verification_button").click()

    assert application is not None
    assert entry.users == []
    assert window.current_route is ShellRoute.LOGIN
