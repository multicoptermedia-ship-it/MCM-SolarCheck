from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from mcm_solarcheck.infrastructure.smtp_email import SMTPConfig, SMTPSecurity
from mcm_solarcheck.services.smtp_admin import SMTPAdminActions, SMTPAdminAuditEvent, SMTPAdminService, SMTPAdminSettingsInput


class Settings:
    def __init__(self) -> None:
        self.config = SMTPConfig("smtp.example.com", 587, "solarcheck@mcm-dronetech.com")

    def get(self) -> SMTPConfig:
        return self.config

    def save(self, config: SMTPConfig) -> None:
        self.config = config


class AllowAdmin:
    def require_admin(self) -> None:
        return None


class DenyAdmin:
    def require_admin(self) -> None:
        raise PermissionError("admin access required")


class AllowMutation:
    def require_mutation_allowed(self) -> None:
        return None


class DenyMutation:
    def require_mutation_allowed(self) -> None:
        raise PermissionError("protected mutation required")


class Audit:
    def __init__(self) -> None:
        self.events: list[SMTPAdminAuditEvent] = []

    def record(self, event: SMTPAdminAuditEvent) -> None:
        self.events.append(event)


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


def test_ui_safe_smtp_test_reports_success_without_secret() -> None:
    secrets = Secrets()
    secrets.replace("super-secret")
    service = SMTPAdminService(Settings(), secrets)

    with patch.object(service, "send_test_email") as send:
        result = service.test_connection()

    send.assert_called_once_with()
    assert result.success is True
    assert "erfolgreich" in result.message
    assert "super-secret" not in repr(result)


def test_ui_safe_smtp_test_hides_provider_error_and_credentials() -> None:
    secrets = Secrets()
    secrets.replace("super-secret")
    service = SMTPAdminService(Settings(), secrets)
    provider_error = (
        "535 authentication failed for solarcheck@mcm-dronetech.com "
        "password=super-secret"
    )

    with patch.object(
        service,
        "send_test_email",
        side_effect=RuntimeError(provider_error),
    ):
        result = service.test_connection()

    assert result.success is False
    assert "fehlgeschlagen" in result.message
    assert "535" not in result.message
    assert "solarcheck@mcm-dronetech.com" not in result.message
    assert "super-secret" not in result.message
    assert provider_error not in repr(result)


def test_admin_view_exposes_only_ui_safe_configuration() -> None:
    settings = Settings()
    settings.config = SMTPConfig(
        "smtp.example.com",
        465,
        "provider-login",
        timeout_seconds=20.0,
        security=SMTPSecurity.TLS,
        sender_address="solarcheck@mcm-dronetech.com",
    )
    secrets = Secrets()
    secrets.replace("super-secret")
    service = SMTPAdminService(settings, secrets)

    view = service.view()

    assert view.host == "smtp.example.com"
    assert view.port == 465
    assert view.username == "provider-login"
    assert view.sender_address == "solarcheck@mcm-dronetech.com"
    assert view.security is SMTPSecurity.TLS
    assert view.timeout_seconds == 20.0
    assert view.password_is_set is True
    assert view.test_recipient == "solarcheck@mcm-dronetech.com"
    assert view.allowed_security == (SMTPSecurity.STARTTLS, SMTPSecurity.TLS)
    assert "password" not in view.__dict__
    assert "super-secret" not in repr(view)
    assert "resolve_for_delivery" not in repr(view)


def test_admin_actions_never_return_replaced_password() -> None:
    settings = Settings()
    secrets = Secrets()
    actions = SMTPAdminActions(SMTPAdminService(settings, secrets), AllowAdmin(), AllowMutation(), Audit())

    view = actions.replace_password("replacement-secret")

    assert secrets.password == "replacement-secret"
    assert view.password_is_set is True
    assert "replacement-secret" not in repr(view)
    assert "password" not in view.__dict__


def test_admin_actions_save_settings_without_changing_secret() -> None:
    settings = Settings()
    secrets = Secrets()
    secrets.replace("existing-secret")
    actions = SMTPAdminActions(SMTPAdminService(settings, secrets), AllowAdmin(), AllowMutation(), Audit())

    view = actions.save_settings(
        SMTPAdminSettingsInput(
            host="smtp.provider.example",
            port=465,
            username="provider-login",
            sender_address="solarcheck@mcm-dronetech.com",
            security=SMTPSecurity.TLS,
            timeout_seconds=15.0,
        )
    )

    assert view.host == "smtp.provider.example"
    assert view.security is SMTPSecurity.TLS
    assert view.password_is_set is True
    assert secrets.password == "existing-secret"


def test_admin_actions_test_email_returns_only_sanitized_result() -> None:
    service = SMTPAdminService(Settings(), Secrets())
    actions = SMTPAdminActions(service, AllowAdmin(), AllowMutation(), Audit())
    provider_error = RuntimeError("535 password=super-secret")

    with patch.object(service, "send_test_email", side_effect=provider_error):
        result = actions.send_test_email()

    assert result.success is False
    assert "fehlgeschlagen" in result.message
    assert "535" not in result.message
    assert "super-secret" not in result.message


@pytest.mark.parametrize("action", ["load", "save", "password", "test"])
def test_smtp_admin_actions_fail_closed_before_service_access(action) -> None:
    settings = Settings()
    secrets = Secrets()
    service = MagicMock(spec=SMTPAdminService)
    actions = SMTPAdminActions(service, DenyAdmin(), AllowMutation(), Audit())

    with pytest.raises(PermissionError, match="admin access"):
        if action == "load":
            actions.load()
        elif action == "save":
            actions.save_settings(
                SMTPAdminSettingsInput(
                    "smtp.example.com",
                    587,
                    "login",
                    "solarcheck@mcm-dronetech.com",
                    SMTPSecurity.STARTTLS,
                )
            )
        elif action == "password":
            actions.replace_password("must-not-be-used")
        else:
            actions.send_test_email()

    service.assert_not_called()
    assert secrets.password is None


@pytest.mark.parametrize("action", ["save", "password", "test"])
def test_smtp_admin_mutations_fail_closed_before_service_access(action) -> None:
    service = MagicMock(spec=SMTPAdminService)
    actions = SMTPAdminActions(service, AllowAdmin(), DenyMutation(), Audit())

    with pytest.raises(PermissionError, match="protected mutation"):
        if action == "save":
            actions.save_settings(
                SMTPAdminSettingsInput(
                    "smtp.example.com",
                    587,
                    "login",
                    "solarcheck@mcm-dronetech.com",
                    SMTPSecurity.STARTTLS,
                )
            )
        elif action == "password":
            actions.replace_password("must-not-be-used")
        else:
            actions.send_test_email()

    service.assert_not_called()


def test_smtp_admin_read_does_not_require_mutation_guard() -> None:
    service = MagicMock(spec=SMTPAdminService)
    expected = MagicMock()
    service.view.return_value = expected
    actions = SMTPAdminActions(service, AllowAdmin(), DenyMutation(), Audit())

    assert actions.load() is expected
    service.view.assert_called_once_with()


def test_smtp_admin_audit_records_only_fixed_secret_free_events() -> None:
    settings = Settings()
    secrets = Secrets()
    audit = Audit()
    service = SMTPAdminService(settings, secrets)
    actions = SMTPAdminActions(service, AllowAdmin(), AllowMutation(), audit)

    actions.replace_password("audit-must-not-see-this-secret")
    actions.save_settings(
        SMTPAdminSettingsInput(
            "smtp.example.com",
            587,
            "login",
            "solarcheck@mcm-dronetech.com",
            SMTPSecurity.STARTTLS,
        )
    )
    with patch.object(service, "test_connection", return_value=MagicMock(success=False)):
        actions.send_test_email()

    assert audit.events == [
        SMTPAdminAuditEvent.PASSWORD_REPLACED,
        SMTPAdminAuditEvent.SETTINGS_CHANGED,
        SMTPAdminAuditEvent.TEST_EMAIL_FAILED,
    ]
    assert "audit-must-not-see-this-secret" not in repr(audit.events)


def test_failed_smtp_admin_change_is_not_audited_as_success() -> None:
    audit = Audit()
    service = MagicMock(spec=SMTPAdminService)
    service.replace_password.side_effect = RuntimeError("secret provider failure")
    actions = SMTPAdminActions(service, AllowAdmin(), AllowMutation(), audit)

    with pytest.raises(RuntimeError, match="provider failure"):
        actions.replace_password("must-not-be-audited")

    assert audit.events == []
