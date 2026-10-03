"""Deployment-aware entry pages for the SolarCheck desktop shell."""

from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.online_registration_controller import RegistrationRequest
from mcm_solarcheck.services.shell_policy import shell_policy


def make_entry_page(
    deployment: DeploymentMode,
    *,
    on_register: Callable[[RegistrationRequest], str | None] | None = None,
    on_email_verification: Callable[[str], str | None] | None = None,
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

        form = QFormLayout()
        fields = {}
        for object_name, label, placeholder in (
            ("registration_user_id", "Benutzer-ID", "Benutzer-ID"),
            ("registration_display_name", "Name / Firma", "Name oder Firma"),
            ("registration_email", "E-Mail", "name@beispiel.de"),
            ("registration_street", "Straße", "Straße und Hausnummer"),
            ("registration_postal_code", "PLZ", "Postleitzahl"),
            ("registration_city", "Ort", "Ort"),
        ):
            field = QLineEdit(page)
            field.setObjectName(object_name)
            field.setPlaceholderText(placeholder)
            fields[object_name] = field
            form.addRow(label, field)
        layout.addLayout(form)

        status = QLabel("", page)
        status.setObjectName("registration_status")
        status.setWordWrap(True)
        layout.addWidget(status)

        register = QPushButton("Registrieren und Bestätigungslink senden", page)
        register.setObjectName("register_button")
        register.setEnabled(on_register is not None)
        if on_register is not None:
            def submit_registration() -> None:
                try:
                    message = on_register(
                        RegistrationRequest(
                        user_id=fields["registration_user_id"].text(),
                        display_name=fields["registration_display_name"].text(),
                        email=fields["registration_email"].text(),
                        street=fields["registration_street"].text(),
                        postal_code=fields["registration_postal_code"].text(),
                        city=fields["registration_city"].text(),
                    )
                    )
                except (ValueError, RuntimeError) as exc:
                    status.setText(str(exc))
                else:
                    status.setText(message or "Registrierung wurde verarbeitet.")
            register.clicked.connect(submit_registration)
        layout.addWidget(register)

        verification_token = QLineEdit(page)
        verification_token.setObjectName("email_verification_token")
        verification_token.setPlaceholderText(
            "Token aus dem Bestätigungslink (normalerweise automatisch übernommen)"
        )
        layout.addWidget(verification_token)

        verification = QPushButton("E-Mail bestätigen", page)
        verification.setObjectName("email_verification_button")
        verification.setToolTip(
            "Bestätigt den serverseitig erzeugten Einmal-Token. "
            "VERIFIED-Status und Produktfreigabe werden nicht in der Oberfläche entschieden."
        )
        verification.setEnabled(on_email_verification is not None)
        if on_email_verification is not None:
            def submit_verification() -> None:
                try:
                    message = on_email_verification(verification_token.text())
                except (ValueError, RuntimeError) as exc:
                    status.setText(str(exc))
                else:
                    status.setText(message or "E-Mail-Verifikation wurde verarbeitet.")
            verification.clicked.connect(submit_verification)
        layout.addWidget(verification)

        verification_hint = QLabel(
            "Nach der Registrierung senden wir einen zeitlich begrenzten "
            "Bestätigungslink an die angegebene E-Mail-Adresse. "
            "Der Link soll den Token automatisch an den Online-Dienst übergeben; "
            "die Eingabe hier dient als sichere Fallback-Grenze. "
            "Erst nach erfolgreicher serverseitiger Bestätigung und Produktfreigabe "
            "wird der Online-Zugang freigeschaltet.",
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
