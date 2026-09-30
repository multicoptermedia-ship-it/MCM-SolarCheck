"""SMTP transport for provider-neutral SolarCheck email messages."""

from __future__ import annotations

import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage as MimeMessage

from mcm_solarcheck.services.email import EmailMessage, EmailSender


@dataclass(frozen=True)
class SMTPConfig:
    """Non-secret SMTP settings suitable for an administrative configuration UI."""

    host: str
    port: int
    username: str
    use_starttls: bool = True
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not isinstance(self.host, str) or not self.host.strip():
            raise ValueError("SMTP host must be non-empty")
        if not isinstance(self.port, int) or not 1 <= self.port <= 65535:
            raise ValueError("SMTP port must be between 1 and 65535")
        if not isinstance(self.username, str) or not self.username.strip():
            raise ValueError("SMTP username must be non-empty")
        if self.timeout_seconds <= 0:
            raise ValueError("SMTP timeout must be positive")


class SMTPEmailSender(EmailSender):
    """Send MIME email via SMTP; the password is injected separately from settings."""

    def __init__(self, config: SMTPConfig, password: str) -> None:
        if not isinstance(password, str) or not password:
            raise ValueError("SMTP password must be provided")
        self._config = config
        self._password = password

    @staticmethod
    def _mime(message: EmailMessage) -> MimeMessage:
        mime = MimeMessage()
        mime["From"] = message.sender
        mime["To"] = message.recipient
        mime["Subject"] = message.subject
        mime.set_content(message.text)
        for attachment in message.attachments:
            if "/" not in attachment.media_type:
                raise ValueError("attachment media_type must contain type/subtype")
            maintype, subtype = attachment.media_type.split("/", 1)
            mime.add_attachment(
                attachment.content,
                maintype=maintype,
                subtype=subtype,
                filename=attachment.filename,
            )
        return mime

    def send(self, message: EmailMessage) -> None:
        mime = self._mime(message)
        with smtplib.SMTP(
            self._config.host,
            self._config.port,
            timeout=self._config.timeout_seconds,
        ) as smtp:
            if self._config.use_starttls:
                smtp.starttls(context=ssl.create_default_context())
            smtp.login(self._config.username, self._password)
            smtp.send_message(mime)
