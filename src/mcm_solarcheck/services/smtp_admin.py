"""Administrative SMTP configuration without exposing stored secrets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from mcm_solarcheck.infrastructure.smtp_email import SMTPConfig, SMTPEmailSender
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
class SMTPAdminStatus:
    host: str
    port: int
    username: str
    use_starttls: bool
    timeout_seconds: float
    password_is_set: bool


class SMTPAdminService:
    def __init__(self, settings: SMTPSettingsStore, secrets: SMTPSecretStore) -> None:
        self._settings = settings
        self._secrets = secrets

    def status(self) -> SMTPAdminStatus:
        config = self._settings.get()
        return SMTPAdminStatus(
            config.host,
            config.port,
            config.username,
            config.use_starttls,
            config.timeout_seconds,
            self._secrets.is_set(),
        )

    def save_settings(self, config: SMTPConfig) -> SMTPAdminStatus:
        self._settings.save(config)
        return self.status()

    def replace_password(self, password: str) -> SMTPAdminStatus:
        if not isinstance(password, str) or not password:
            raise ValueError("SMTP password must be provided")
        self._secrets.replace(password)
        return self.status()

    def send_test_email(self) -> None:
        config = self._settings.get()
        password = self._secrets.resolve_for_delivery()
        SMTPEmailSender(config, password).send(
            EmailMessage(
                sender=config.username,
                recipient=ADMIN_NOTIFICATION_EMAIL,
                subject="SolarCheck SMTP-Test",
                text=(
                    "Diese Testmail bestätigt, dass die konfigurierte "
                    "SolarCheck-SMTP-Verbindung funktioniert."
                ),
            )
        )
