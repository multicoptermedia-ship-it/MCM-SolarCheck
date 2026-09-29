from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from mcm_solarcheck.infrastructure.sqlite_registration import (
    SQLiteOnlineRegistrationStore,
)
from mcm_solarcheck.services.email import EmailMessage, RegistrationEmailConfig
from mcm_solarcheck.services.online_entitlement import OnlineProduct
from mcm_solarcheck.services.online_registration import OnlineRegistrationService
from mcm_solarcheck.services.registration import RegistrationStatus


class RecordingEmailSender:
    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.messages.append(message)


def test_registration_verification_and_entitlement_workflow(tmp_path) -> None:
    store = SQLiteOnlineRegistrationStore(tmp_path / "registration.sqlite")
    sender = RecordingEmailSender()
    service = OnlineRegistrationService(
        store,
        sender,
        RegistrationEmailConfig(
            sender="solarcheck@mcm-solarcheck.de",
            notify_to="solarcheck@mcm-dronetech.com",
            public_base_url="https://app.mcm-solarcheck.de",
        ),
        verification_duration=timedelta(minutes=30),
    )
    start = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)

    pending = service.register(
        user_id="user-a",
        display_name="MCM Dronetech",
        email="User@Example.com",
        now=start,
    )

    assert pending.status is RegistrationStatus.PENDING
    assert len(sender.messages) == 1
    verification_mail = sender.messages[0]
    assert verification_mail.recipient == "user@example.com"
    link = next(
        line for line in verification_mail.text.splitlines()
        if line.startswith("https://")
    )
    token = parse_qs(urlparse(link).query)["token"][0]

    entitlement = service.verify_and_activate(
        token,
        product=OnlineProduct.TRIAL,
        now=start + timedelta(minutes=1),
    )

    assert entitlement.user_id == "user-a"
    assert entitlement.product is OnlineProduct.TRIAL
    assert entitlement.active
    assert store.get("user-a").status is RegistrationStatus.VERIFIED
    assert len(sender.messages) == 2
    audit_mail = sender.messages[1]
    assert audit_mail.recipient == "solarcheck@mcm-dronetech.com"
    assert token not in audit_mail.text
    assert "user@example.com" in audit_mail.text
