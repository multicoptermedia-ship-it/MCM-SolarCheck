from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mcm_solarcheck.services.email import EmailMessage, RegistrationEmailConfig
from mcm_solarcheck.services.registration import OnlineRegistration
from mcm_solarcheck.services.registration_notification import (
    RegistrationNotificationService,
)


class RecordingEmailSender:
    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.messages.append(message)


def test_verified_registration_sends_internal_audit_notification() -> None:
    sender = RecordingEmailSender()
    service = RegistrationNotificationService(
        sender,
        RegistrationEmailConfig(
            sender="solarcheck@mcm-solarcheck.de",
            notify_to="solarcheck@mcm-dronetech.com",
            public_base_url="https://app.mcm-solarcheck.de",
        ),
    )
    registration = OnlineRegistration(
        "user-a", "MCM Dronetech", "user@example.com"
    ).verify(datetime(2026, 9, 29, 11, 0, tzinfo=timezone.utc))

    service.notify_verified(registration)

    assert len(sender.messages) == 1
    message = sender.messages[0]
    assert message.recipient == "solarcheck@mcm-dronetech.com"
    assert "user-a" in message.text
    assert "MCM Dronetech" in message.text
    assert "user@example.com" in message.text
    assert "secret" not in message.text.lower()
    assert "token" not in message.text.lower()


def test_pending_registration_cannot_trigger_internal_notification() -> None:
    sender = RecordingEmailSender()
    service = RegistrationNotificationService(
        sender,
        RegistrationEmailConfig(
            sender="solarcheck@mcm-solarcheck.de",
            notify_to="solarcheck@mcm-dronetech.com",
            public_base_url="https://app.mcm-solarcheck.de",
        ),
    )

    with pytest.raises(ValueError, match="verified"):
        service.notify_verified(
            OnlineRegistration(
                "user-a", "MCM Dronetech", "user@example.com"
            )
        )

    assert sender.messages == []
