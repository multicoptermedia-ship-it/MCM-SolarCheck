"""SMTP transport for provider-neutral SolarCheck email messages."""

from __future__ import annotations

import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage as MimeMessage
from enum import Enum

from mcm_solarcheck.services.email import EmailMessage, EmailSender


class SMTPSecurity(str, Enum):
    STARTTLS = "starttls"
    TLS = "tls"


@dataclass(frozen=True)
class SMTPConfig:
    """Non-secret SMTP settings suitable for an administrative configuration UI."""

    host: str
    port: int
    username: str
    use_starttls: bool = True
    timeout_seconds: float = 30.0
    security: SMTPSecurity | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.host, str) or not self.host.strip():
            raise ValueError("SMTP host must be non-empty")
        if not isinstance(self.port, int) or not 1 <= self.port <= 65535:
            raise ValueError("SMTP port must be between 1 and 65535")
        if not isinstance(self.username, str) or not self.username.strip():
            raise ValueError("SMTP username must be non-empty")
        if self.timeout_seconds <= 0:
            raise ValueError("SMTP timeout must be positive")
        if self.security is not None and not isinstance(self.security, SMTPSecurity):
            raise ValueError("SMTP security must be STARTTLS or TLS")

    @property
    def security_mode(self) -> SMTPSecurity:
        if self.security is not None:
            return self.security
        if self.use_starttls:
            return SMTPSecurity.STARTTLS
        raise ValueError("unencrypted SMTP is not supported")


class SMTPEmailSender(EmailSender):
    """Send MIME email via encrypted SMTP; the password is injected separately."""

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
        context = ssl.create_default_context()
        if self._config.security_mode is SMTPSecurity.TLS:
            connection = smtplib.SMTP_SSL(
                self._config.host,
                self._config.port,
                timeout=self._config.timeout_seconds,
                context=context,
            )
        else:
            connection = smtplib.SMTP(
                self._config.host,
                self._config.port,
                timeout=self._config.timeout_seconds,
            )
        with connection as smtp:
            if self._config.security_mode is SMTPSecurity.STARTTLS:
                smtp.starttls(context=context)
            smtp.login(self._config.username, self._password)
            smtp.send_message(mime)
