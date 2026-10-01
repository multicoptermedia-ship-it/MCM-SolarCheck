"""Administrative SMTP configuration without exposing stored secrets."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from mcm_solarcheck.infrastructure.smtp_email import SMTPConfig, SMTPEmailSender, SMTPSecurity
from mcm_solarcheck.services.admin_notification import ADMIN_NOTIFICATION_EMAIL
from mcm_solarcheck.services.email import EmailMessage


class SMTPSettingsStore(Protocol):
    def get(self) -> SMTPConfig:
        ...

    def save(self, config: SMTPConfig) -> None:
        ...


class SMTPSecretStore(Protocol):
    """Write-only from the administrative UI's perspective."""

    def is_set(self) -> bool:
        ...

    def replace(self, password: str) -> None:
        ...

    def resolve_for_delivery(self) -> str:
        """Internal delivery use only; never expose this through an admin response."""
        ...


@dataclass(frozen=True)
class SMTPAdminSettingsInput:
    """Non-secret values accepted from a future administrative UI."""

    host: str
    port: int
    username: str
    sender_address: str
    security: SMTPSecurity
    timeout_seconds: float = 30.0

    def to_config(self) -> SMTPConfig:
        if not isinstance(self.security, SMTPSecurity):
            raise ValueError("SMTP security must be STARTTLS or TLS")
        return SMTPConfig(
            host=self.host,
            port=self.port,
            username=self.username,
            timeout_seconds=self.timeout_seconds,
            security=self.security,
            sender_address=self.sender_address,
        )


@dataclass(frozen=True)
class SMTPTestResult:
    success: bool
    message: str


@dataclass(frozen=True)
class SMTPAdminView:
    """UI-safe SMTP administration model containing no secret value."""

    host: str
    port: int
    username: str
    sender_address: str
    security: SMTPSecurity
    timeout_seconds: float
    password_is_set: bool
    test_recipient: str
    allowed_security: tuple[SMTPSecurity, ...]


@dataclass(frozen=True)
class SMTPAdminStatus:
    host: str
    port: int
    username: str
    use_starttls: bool
    timeout_seconds: float
    password_is_set: bool
    security: SMTPSecurity
    sender_address: str


class SMTPAdminAuthorization(Protocol):
    """Authorization boundary supplied by the future online application."""

    def require_admin(self) -> None:
        ...


class SMTPAdminMutationGuard(Protocol):
    """Confirm that a state-changing admin request is intentional and protected."""

    def require_mutation_allowed(self) -> None:
        ...


class SMTPAdminAuditEvent(str, Enum):
    SETTINGS_CHANGED = "settings_changed"
    PASSWORD_REPLACED = "password_replaced"
    TEST_EMAIL_SUCCEEDED = "test_email_succeeded"
    TEST_EMAIL_FAILED = "test_email_failed"


class SMTPAdminAudit(Protocol):
    """Record fixed, secret-free SMTP administration events."""

    def record(self, event: SMTPAdminAuditEvent) -> None:
        ...


class SMTPAdminActions:
    """Framework-neutral actions exposed to a future administrative UI."""

    def __init__(
        self,
        service: "SMTPAdminService",
        authorization: SMTPAdminAuthorization,
        mutation_guard: SMTPAdminMutationGuard,
        audit: SMTPAdminAudit,
    ) -> None:
        required = (
            (service, "view", "service"),
            (authorization, "require_admin", "authorization"),
            (mutation_guard, "require_mutation_allowed", "mutation_guard"),
            (audit, "record", "audit"),
        )
        for dependency, method, name in required:
            if not callable(getattr(dependency, method, None)):
                raise TypeError(f"{name} must provide {method}()")
        self._service = service
        self._authorization = authorization
        self._mutation_guard = mutation_guard
        self._audit = audit

    def load(self) -> SMTPAdminView:
        self._authorization.require_admin()
        return self._service.view()

    def save_settings(self, values: SMTPAdminSettingsInput) -> SMTPAdminView:
        self._authorization.require_admin()
        self._mutation_guard.require_mutation_allowed()
        self._service.save_admin_settings(values)
        self._audit.record(SMTPAdminAuditEvent.SETTINGS_CHANGED)
        return self._service.view()

    def replace_password(self, password: str) -> SMTPAdminView:
        self._authorization.require_admin()
        self._mutation_guard.require_mutation_allowed()
        self._service.replace_password(password)
        self._audit.record(SMTPAdminAuditEvent.PASSWORD_REPLACED)
        return self._service.view()

    def send_test_email(self) -> SMTPTestResult:
        self._authorization.require_admin()
        self._mutation_guard.require_mutation_allowed()
        result = self._service.test_connection()
        self._audit.record(
            SMTPAdminAuditEvent.TEST_EMAIL_SUCCEEDED
            if result.success
            else SMTPAdminAuditEvent.TEST_EMAIL_FAILED
        )
        return result


class SMTPAdminService:
    def __init__(self, settings: SMTPSettingsStore, secrets: SMTPSecretStore) -> None:
        required = (
            (settings, "get", "settings"),
            (settings, "save", "settings"),
            (secrets, "is_set", "secrets"),
            (secrets, "replace", "secrets"),
            (secrets, "resolve_for_delivery", "secrets"),
        )
        for dependency, method, name in required:
            if not callable(getattr(dependency, method, None)):
                raise TypeError(f"{name} must provide {method}()")
        self._settings = settings
        self._secrets = secrets

    def view(self) -> SMTPAdminView:
        """Return only values that an administrative UI may display."""
        status = self.status()
        return SMTPAdminView(
            host=status.host,
            port=status.port,
            username=status.username,
            sender_address=status.sender_address,
            security=status.security,
            timeout_seconds=status.timeout_seconds,
            password_is_set=status.password_is_set,
            test_recipient=ADMIN_NOTIFICATION_EMAIL,
            allowed_security=(SMTPSecurity.STARTTLS, SMTPSecurity.TLS),
        )

    def status(self) -> SMTPAdminStatus:
        config = self._settings.get()
        return SMTPAdminStatus(
            config.host,
            config.port,
            config.username,
            config.use_starttls,
            config.timeout_seconds,
            self._secrets.is_set(),
            config.security_mode,
            config.effective_sender_address,
        )

    def save_settings(self, config: SMTPConfig) -> SMTPAdminStatus:
        self._settings.save(config)
        return self.status()

    def save_admin_settings(self, values: SMTPAdminSettingsInput) -> SMTPAdminStatus:
        config = values.to_config()
        self._settings.save(config)
        return self.status()

    def replace_password(self, password: str) -> SMTPAdminStatus:
        if not isinstance(password, str) or not password:
            raise ValueError("SMTP password must be provided")
        self._secrets.replace(password)
        return self.status()

    def test_connection(self) -> SMTPTestResult:
        """UI-safe SMTP test result without exposing provider errors or secrets."""
        try:
            self.send_test_email()
        except Exception:
            return SMTPTestResult(
                False,
                "SMTP-Test fehlgeschlagen. Bitte Einstellungen und Zugangsdaten prüfen.",
            )
        return SMTPTestResult(True, "SMTP-Testmail wurde erfolgreich versendet.")

    def send_test_email(self) -> None:
        config = self._settings.get()
        password = self._secrets.resolve_for_delivery()
        SMTPEmailSender(config, password).send(
            EmailMessage(
                sender=config.effective_sender_address,
                recipient=ADMIN_NOTIFICATION_EMAIL,
                subject="SolarCheck SMTP-Test",
                text=(
                    "Diese Testmail bestätigt, dass die konfigurierte "
                    "SolarCheck-SMTP-Verbindung funktioniert."
                ),
            )
        )
