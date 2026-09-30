from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from mcm_solarcheck.infrastructure.smtp_email import SMTPConfig
from mcm_solarcheck.services.smtp_admin import SMTPAdminService


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
