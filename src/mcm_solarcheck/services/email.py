"""Provider-neutral email delivery contracts for SolarCheck."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote, urlparse


@dataclass(frozen=True)
class EmailMessage:
    """Transport-neutral email message."""

    sender: str
    recipient: str
    subject: str
    text: str

    def __post_init__(self) -> None:
        for name, value in (
            ("sender", self.sender),
            ("recipient", self.recipient),
            ("subject", self.subject),
            ("text", self.text),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")


class EmailSender(Protocol):
    """Delivery boundary implemented later by SMTP or another provider."""

    def send(self, message: EmailMessage) -> None:
        """Deliver one email message."""
        ...


@dataclass(frozen=True)
class RegistrationEmailConfig:
    """Deployment-owned addresses and public application URL."""

    sender: str
    notify_to: str
    public_base_url: str

    def __post_init__(self) -> None:
        for address in (self.sender, self.notify_to):
            if address.count("@") != 1:
                raise ValueError("configured email address must be plausible")
        parsed = urlparse(self.public_base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("public_base_url must be an absolute HTTP(S) URL")

    def verification_url(self, token: str) -> str:
        if not isinstance(token, str) or not token.strip():
            raise ValueError("verification token must be non-empty")
        return (
            self.public_base_url.rstrip("/")
            + "/verify-email?token="
            + quote(token, safe="")
        )


@dataclass(frozen=True)
class ReportRecoveryEmailConfig:
    """Deployment-owned addresses for internal report recovery alerts."""

    sender: str
    notify_to: str

    def __post_init__(self) -> None:
        for address in (self.sender, self.notify_to):
            if address.count("@") != 1:
                raise ValueError("configured email address must be plausible")
