"""Notification boundary for successfully verified online registrations."""

from __future__ import annotations

from mcm_solarcheck.services.admin_notification import ADMIN_NOTIFICATION_EMAIL
from mcm_solarcheck.services.email import (
    EmailMessage,
    EmailSender,
    RegistrationEmailConfig,
)
from mcm_solarcheck.services.registration import OnlineRegistration, RegistrationStatus


class RegistrationNotificationService:
    """Notify operations only from authoritative verified registration state."""

    def __init__(
        self,
        sender: EmailSender,
        config: RegistrationEmailConfig,
    ) -> None:
        self._sender = sender
        self._config = config

    def notify_verified(self, registration: OnlineRegistration) -> None:
        if registration.status is not RegistrationStatus.VERIFIED:
            raise ValueError("registration must be verified before notification")
        if registration.verified_at is None:
            raise ValueError("verified registration requires verified_at")

        self._sender.send(
            EmailMessage(
                sender=self._config.sender,
                recipient=ADMIN_NOTIFICATION_EMAIL,
                subject="SolarCheck Online: E-Mail verifiziert",
                text=(
                    "Eine Online-Registrierung wurde erfolgreich verifiziert.\n\n"
                    f"Benutzer-ID: {registration.user_id}\n"
                    f"Name/Firma: {registration.display_name}\n"
                    f"E-Mail: {registration.email}\n"
                    f"Verifiziert am: {registration.verified_at.isoformat()}\n"
                ),
            )
        )
