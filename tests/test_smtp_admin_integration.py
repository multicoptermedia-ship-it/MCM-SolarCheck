from __future__ import annotations

from unittest.mock import MagicMock, patch

from mcm_solarcheck.infrastructure.environment_smtp_secret import EnvironmentSMTPSecretStore
from mcm_solarcheck.infrastructure.smtp_email import SMTPConfig
from mcm_solarcheck.infrastructure.sqlite_smtp_settings import SQLiteSMTPSettingsStore
from mcm_solarcheck.services.smtp_admin import SMTPAdminService


def test_persisted_smtp_admin_configuration_drives_test_email(tmp_path) -> None:
    settings = SQLiteSMTPSettingsStore(
        tmp_path / "solarcheck.sqlite",
        SMTPConfig("smtp.initial.example", 587, "solarcheck@mcm-dronetech.com"),
    )
    environment: dict[str, str] = {}
    service = SMTPAdminService(
        settings,
        EnvironmentSMTPSecretStore(environment=environment),
    )
    configured = SMTPConfig(
        "smtp.production.example",
        587,
        "solarcheck@mcm-dronetech.com",
        True,
        20.0,
    )

    service.save_settings(configured)
    service.replace_password("test-value")

    sender = MagicMock()
    with patch(
        "mcm_solarcheck.services.smtp_admin.SMTPEmailSender",
        return_value=sender,
    ) as sender_type:
        service.send_test_email()

    sender_type.assert_called_once_with(configured, "test-value")
    message = sender.send.call_args.args[0]
    assert message.sender == "solarcheck@mcm-dronetech.com"
    assert message.recipient == "solarcheck@mcm-dronetech.com"
    assert message.subject == "SolarCheck SMTP-Test"
    assert service.status().password_is_set is True
