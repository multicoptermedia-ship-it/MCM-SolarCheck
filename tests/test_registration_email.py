from __future__ import annotations

import pytest

from mcm_solarcheck.services.email import EmailMessage, RegistrationEmailConfig


def test_registration_email_config_builds_verification_url() -> None:
    config = RegistrationEmailConfig(
        sender="solarcheck@mcm-solarcheck.de",
        notify_to="solarcheck@mcm-dronetech.com",
        public_base_url="https://app.mcm-solarcheck.de/",
    )

    assert config.verification_url("a token/+?") == (
        "https://app.mcm-solarcheck.de/verify-email?token=a%20token%2F%2B%3F"
    )


def test_registration_email_config_is_provider_neutral() -> None:
    inwx = RegistrationEmailConfig(
        sender="solarcheck@mcm-dronetech.com",
        notify_to="solarcheck@mcm-dronetech.com",
        public_base_url="https://app.mcm-solarcheck.de",
    )
    ionos = RegistrationEmailConfig(
        sender="solarcheck@mcm-solarcheck.de",
        notify_to="solarcheck@mcm-solarcheck.de",
        public_base_url="https://app.mcm-solarcheck.de",
    )

    assert inwx.public_base_url == ionos.public_base_url
    assert inwx.sender != ionos.sender


@pytest.mark.parametrize(
    "base_url",
    ["app.mcm-solarcheck.de", "/verify", "ftp://app.mcm-solarcheck.de"],
)
def test_registration_email_config_requires_absolute_http_url(base_url: str) -> None:
    with pytest.raises(ValueError, match="absolute HTTP"):
        RegistrationEmailConfig(
            sender="solarcheck@mcm-solarcheck.de",
            notify_to="solarcheck@mcm-dronetech.com",
            public_base_url=base_url,
        )


def test_email_message_requires_complete_transport_neutral_content() -> None:
    message = EmailMessage(
        sender="solarcheck@mcm-solarcheck.de",
        recipient="user@example.com",
        subject="SolarCheck E-Mail bestätigen",
        text="Bitte bestätigen Sie Ihre E-Mail-Adresse.",
    )

    assert message.recipient == "user@example.com"
