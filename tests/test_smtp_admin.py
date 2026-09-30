from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from mcm_solarcheck.infrastructure.smtp_email import SMTPConfig, SMTPSecurity
from mcm_solarcheck.services.smtp_admin import SMTPAdminService, SMTPAdminSettingsInput


class Settings:
    def __init__(self) -> None:
        self.config = SMTPConfig("smtp.example.com", 587, "solarcheck@mcm-dronetech.com")

    def get(self) -> SMTPConfig:
        return self.config

    def save(self, config: SMTPConfig) -> None:
        self.config = config


class Secrets:
    def __init__(self) -> None:
        self.password: str | None = None

    def is_set(self) -> bool:
        return self.password is not None

    def replace(self, password: str) -> None:
        self.password = password

    def resolve_for_delivery(self) -> str:
        if self.password is None:
            raise RuntimeError("SMTP password is not configured")
        return self.password


def test_admin_status_never_contains_password() -> None:
    settings = Settings()
    secrets = Secrets()
    secrets.replace("super-secret")
    service = SMTPAdminService(settings, secrets)

    status = service.status()

    assert status.password_is_set is True
    assert "password" not in status.__dict__
    assert "super-secret" not in repr(status)


def test_admin_can_replace_password_without_returning_it() -> None:
    service = SMTPAdminService(Settings(), Secrets())

    status = service.replace_password("new-secret")

    assert status.password_is_set is True
    assert "new-secret" not in repr(status)


def test_admin_rejects_empty_password() -> None:
    service = SMTPAdminService(Settings(), Secrets())

    with pytest.raises(ValueError, match="password"):
        service.replace_password("")


def test_test_email_uses_configured_account_and_admin_destination() -> None:
    settings = Settings()
    secrets = Secrets()
    secrets.replace("secret")
    service = SMTPAdminService(settings, secrets)
    sender = MagicMock()

    with patch(
        "mcm_solarcheck.services.smtp_admin.SMTPEmailSender",
        return_value=sender,
    ) as sender_type:
        service.send_test_email()

    sender_type.assert_called_once_with(settings.config, "secret")
    message = sender.send.call_args.args[0]
    assert message.sender == "solarcheck@mcm-dronetech.com"
    assert message.recipient == "solarcheck@mcm-dronetech.com"
    assert message.subject == "SolarCheck SMTP-Test"


def test_admin_keeps_smtp_login_separate_from_visible_sender() -> None:
    settings = Settings()
    settings.config = SMTPConfig(
        "smtp.example.com",
        587,
        "provider-login",
        sender_address="solarcheck@mcm-dronetech.com",
    )
    secrets = Secrets()
    secrets.replace("secret")
    service = SMTPAdminService(settings, secrets)
    sender = MagicMock()

    status = service.status()
    assert status.username == "provider-login"
    assert status.sender_address == "solarcheck@mcm-dronetech.com"

    with patch(
        "mcm_solarcheck.services.smtp_admin.SMTPEmailSender",
        return_value=sender,
    ) as sender_type:
        service.send_test_email()

    sender_type.assert_called_once_with(settings.config, "secret")
    message = sender.send.call_args.args[0]
    assert message.sender == "solarcheck@mcm-dronetech.com"
    assert message.recipient == "solarcheck@mcm-dronetech.com"
    assert "provider-login" not in message.text


def test_admin_settings_input_saves_only_non_secret_secure_values() -> None:
    settings = Settings()
    secrets = Secrets()
    secrets.replace("existing-secret")
    service = SMTPAdminService(settings, secrets)

    status = service.save_admin_settings(
        SMTPAdminSettingsInput(
            host="smtp.provider.example",
            port=465,
            username="technical-login",
            sender_address="solarcheck@mcm-dronetech.com",
            security=SMTPSecurity.TLS,
            timeout_seconds=20.0,
        )
    )

    assert settings.config.host == "smtp.provider.example"
    assert settings.config.security_mode is SMTPSecurity.TLS
    assert status.sender_address == "solarcheck@mcm-dronetech.com"
    assert status.password_is_set is True
    assert secrets.password == "existing-secret"


@pytest.mark.parametrize(
    "values, message",
    [
        (
            SMTPAdminSettingsInput("", 587, "login", "solarcheck@mcm-dronetech.com", SMTPSecurity.STARTTLS),
            "host",
        ),
        (
            SMTPAdminSettingsInput("smtp.example.com", 0, "login", "solarcheck@mcm-dronetech.com", SMTPSecurity.STARTTLS),
            "port",
        ),
        (
            SMTPAdminSettingsInput("smtp.example.com", 587, "", "solarcheck@mcm-dronetech.com", SMTPSecurity.STARTTLS),
            "username",
        ),
        (
            SMTPAdminSettingsInput("smtp.example.com", 587, "login", "", SMTPSecurity.STARTTLS),
            "sender",
        ),
    ],
)
def test_admin_rejects_invalid_settings_before_save(values, message) -> None:
    settings = Settings()
    service = SMTPAdminService(settings, Secrets())
    original = settings.config

    with pytest.raises(ValueError, match=message):
        service.save_admin_settings(values)

    assert settings.config == original


def test_admin_input_rejects_unencrypted_security_value() -> None:
    settings = Settings()
    service = SMTPAdminService(settings, Secrets())
    values = SMTPAdminSettingsInput(
        "smtp.example.com",
        587,
        "login",
        "solarcheck@mcm-dronetech.com",
        "plain",  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="security"):
        service.save_admin_settings(values)
