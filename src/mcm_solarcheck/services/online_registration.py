"""Server-owned workflow for online registration and email verification."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Protocol

from mcm_solarcheck.services.email import (
    EmailMessage,
    EmailSender,
    RegistrationEmailConfig,
)
from mcm_solarcheck.services.online_entitlement import (
    OnlineEntitlement,
    OnlineEntitlementService,
    OnlineProduct,
)
from mcm_solarcheck.services.registration import OnlineRegistration
from mcm_solarcheck.services.registration_notification import (
    RegistrationNotificationService,
)


class OnlineRegistrationStore(Protocol):
    def create(
        self,
        registration: OnlineRegistration,
        *,
        token: str,
        expires_at: datetime,
    ) -> None:
        ...

    def verify(self, token: str, *, now: datetime) -> OnlineRegistration:
        ...


class OnlineRegistrationService:
    """Coordinate registration, verification, notification and entitlement."""

    def __init__(
        self,
        store: OnlineRegistrationStore,
        email_sender: EmailSender,
        email_config: RegistrationEmailConfig,
        *,
        verification_duration: timedelta = timedelta(minutes=30),
    ) -> None:
        if verification_duration <= timedelta(0):
            raise ValueError("verification_duration must be positive")
        self._store = store
        self._email_sender = email_sender
        self._email_config = email_config
        self._verification_duration = verification_duration
        self._notifications = RegistrationNotificationService(
            email_sender, email_config
        )
        self._entitlements = OnlineEntitlementService()

    def register(
        self,
        *,
        user_id: str,
        display_name: str,
        email: str,
        now: datetime,
    ) -> OnlineRegistration:
        registration = OnlineRegistration(user_id, display_name, email)
        token = secrets.token_urlsafe(32)
        self._store.create(
            registration,
            token=token,
            expires_at=now + self._verification_duration,
        )
        self._email_sender.send(
            EmailMessage(
                sender=self._email_config.sender,
                recipient=registration.email,
                subject="SolarCheck E-Mail-Adresse bestätigen",
                text=(
                    "Bitte bestätigen Sie Ihre E-Mail-Adresse für SolarCheck Online:\n\n"
                    f"{self._email_config.verification_url(token)}\n\n"
                    "Wenn Sie diese Registrierung nicht angefordert haben, "
                    "können Sie diese Nachricht ignorieren."
                ),
            )
        )
        return registration

    def verify_and_activate(
        self,
        token: str,
        *,
        product: OnlineProduct,
        now: datetime,
    ) -> OnlineEntitlement:
        registration = self._store.verify(token, now=now)
        entitlement = self._entitlements.activate(
            OnlineEntitlement(registration.user_id, product),
            registration,
        )
        self._notifications.notify_verified(registration)
        return entitlement
