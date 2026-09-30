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

    sender_type.assert_called_once()
    persisted_config, persisted_password = sender_type.call_args.args
    assert persisted_password == "test-value"
    assert persisted_config.host == configured.host
    assert persisted_config.port == configured.port
    assert persisted_config.username == configured.username
    assert persisted_config.timeout_seconds == configured.timeout_seconds
    assert persisted_config.security_mode == configured.security_mode
    assert persisted_config.effective_sender_address == configured.effective_sender_address
    message = sender.send.call_args.args[0]
    assert message.sender == "solarcheck@mcm-dronetech.com"
    assert message.recipient == "solarcheck@mcm-dronetech.com"
    assert message.subject == "SolarCheck SMTP-Test"
    assert service.status().password_is_set is True
