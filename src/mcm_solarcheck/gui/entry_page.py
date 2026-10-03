"""Deployment-aware entry pages for the SolarCheck desktop shell."""

from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.shell_policy import shell_policy


def make_entry_page(
    deployment: DeploymentMode,
    *,
    on_register: Callable[[], None] | None = None,
    on_email_verification: Callable[[], None] | None = None,
) -> QWidget:
    """Build the deployment entry page without duplicating product policy."""
    policy = shell_policy(deployment)
    page = QWidget()
    layout = QVBoxLayout(page)

    if policy.show_login:
        page.setObjectName("login_page")
        heading = QLabel("SolarCheck", page)
        heading.setObjectName("page_heading")
        layout.addWidget(heading)

        provider = QLabel("powered by MCM-Dronetech GmbH", page)
        provider.setObjectName("provider_attribution")
        layout.addWidget(provider)

        login_hint = QLabel(
            "Anmelden, um SolarCheck Online zu verwenden. "
            "Neue Konten müssen zuerst per E-Mail bestätigt werden.",
            page,
        )
        login_hint.setObjectName("login_hint")
        login_hint.setWordWrap(True)
        layout.addWidget(login_hint)

        register = QPushButton("Registrieren", page)
        register.setObjectName("register_button")
        register.setEnabled(on_register is not None)
        if on_register is not None:
            register.clicked.connect(on_register)
        layout.addWidget(register)

        verification = QPushButton("E-Mail bestätigen", page)
        verification.setObjectName("email_verification_button")
        verification.setToolTip(
            "Öffnet den serverseitigen Bestätigungsablauf. "
            "Der Einmal-Token wird nicht in der Oberfläche gespeichert."
        )
        verification.setEnabled(on_email_verification is not None)
        if on_email_verification is not None:
            verification.clicked.connect(on_email_verification)
        layout.addWidget(verification)

        verification_hint = QLabel(
            "Nach der Registrierung senden wir einen zeitlich begrenzten "
            "Bestätigungslink an die angegebene E-Mail-Adresse. "
            "Erst nach erfolgreicher Bestätigung wird der Online-Zugang freigeschaltet.",
            page,
        )
        verification_hint.setObjectName("email_verification_hint")
        verification_hint.setWordWrap(True)
        layout.addWidget(verification_hint)

        if policy.show_user_guide_hint:
            guide_hint = QLabel(
                "Die Bedienungsanleitung finden Sie jederzeit im Menü Hilfe.",
                page,
            )
            guide_hint.setObjectName("user_guide_hint")
            layout.addWidget(guide_hint)
    else:
        page.setObjectName("project_page")
        heading = QLabel("Projekt", page)
        heading.setObjectName("page_heading")
        layout.addWidget(heading)

    return page
