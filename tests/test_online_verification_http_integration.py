from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
from threading import Thread
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen

import pytest

from mcm_solarcheck.infrastructure.sqlite_online_entitlement import SQLiteOnlineEntitlementStore
from mcm_solarcheck.infrastructure.sqlite_registration import SQLiteOnlineRegistrationStore
from mcm_solarcheck.online.http_entrypoint import build_online_verification_server
from mcm_solarcheck.online.product import OnlineProduct
from mcm_solarcheck.services.email import EmailMessage, RegistrationEmailConfig
from mcm_solarcheck.services.online_entitlement import OnlineProduct as EntitlementProduct
from mcm_solarcheck.services.online_registration import OnlineRegistrationService
from mcm_solarcheck.services.registration import RegistrationStatus


class Sender:
    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.messages.append(message)


class Services:
    def __init__(self, registration, entitlements) -> None:
        self.registration = registration
        self.entitlements = entitlements


def test_http_deep_link_verifies_registration_and_persists_entitlement(tmp_path) -> None:
    registrations = SQLiteOnlineRegistrationStore(tmp_path / "registration.sqlite")
    entitlements = SQLiteOnlineEntitlementStore(tmp_path / "entitlements.sqlite")
    sender = Sender()
    start = datetime(2026, 10, 3, 18, 0, tzinfo=timezone.utc)
    registration = OnlineRegistrationService(
        registrations,
        sender,
        RegistrationEmailConfig(
            sender="solarcheck@mcm-solarcheck.de",
            notify_to="solarcheck@mcm-dronetech.com",
            public_base_url="https://app.mcm-solarcheck.de",
        ),
        entitlements=entitlements,
        verification_duration=timedelta(minutes=30),
    )
    registration.register(
        user_id="user-1",
        display_name="MCM Test",
        email="user@example.com",
        street="Musterweg 1",
        postal_code="50181",
        city="Bedburg",
        now=start,
    )
    link = next(line for line in sender.messages[0].text.splitlines() if line.startswith("https://"))
    token = parse_qs(urlparse(link).query)["token"][0]

    product = OnlineProduct.compose(Services(registration, entitlements))
    server = build_online_verification_server(
        product,
        now=lambda: start + timedelta(minutes=1),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        with closing(
            urlopen(f"http://{host}:{port}/verify-email?token={token}", timeout=2)
        ) as response:
            assert response.status == 200
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert registrations.get("user-1").status is RegistrationStatus.VERIFIED
    entitlement = entitlements.require_active("user-1")
    assert entitlement.product is EntitlementProduct.TRIAL
    assert entitlement.active


def test_production_http_requires_secure_session_cookies(tmp_path) -> None:
    registrations = SQLiteOnlineRegistrationStore(tmp_path / "registration.sqlite")
    entitlements = SQLiteOnlineEntitlementStore(tmp_path / "entitlements.sqlite")
    sender = Sender()
    registration = OnlineRegistrationService(
        registrations,
        sender,
        RegistrationEmailConfig(
            sender="solarcheck@mcm-solarcheck.de",
            notify_to="solarcheck@mcm-dronetech.com",
            public_base_url="https://app.mcm-solarcheck.de",
        ),
        entitlements=entitlements,
    )
    product = OnlineProduct.compose(Services(registration, entitlements))

    with pytest.raises(ValueError, match="production HTTP requires secure session cookies"):
        build_online_verification_server(product, production=True)


def test_production_http_accepts_explicit_secure_session_cookies(tmp_path) -> None:
    registrations = SQLiteOnlineRegistrationStore(tmp_path / "registration.sqlite")
    entitlements = SQLiteOnlineEntitlementStore(tmp_path / "entitlements.sqlite")
    sender = Sender()
    registration = OnlineRegistrationService(
        registrations,
        sender,
        RegistrationEmailConfig(
            sender="solarcheck@mcm-solarcheck.de",
            notify_to="solarcheck@mcm-dronetech.com",
            public_base_url="https://app.mcm-solarcheck.de",
        ),
        entitlements=entitlements,
    )
    product = OnlineProduct.compose(Services(registration, entitlements))

    server = build_online_verification_server(
        product,
        production=True,
        secure_cookies=True,
    )
    try:
        assert server.server_address
    finally:
        server.server_close()
