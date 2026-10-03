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
    OnlineEntitlementStore,
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

    def get(self, user_id: str) -> OnlineRegistration:
        ...

    def pending_notification_user_ids(self) -> list[str]:
        ...

    def mark_notification_sent(self, user_id: str, *, now: datetime) -> None:
        ...


class OnlineRegistrationService:
    """Coordinate registration, verification, notification and entitlement."""

    def __init__(
        self,
        store: OnlineRegistrationStore,
        email_sender: EmailSender,
        email_config: RegistrationEmailConfig,
        *,
        entitlements: OnlineEntitlementStore | None = None,
        verification_duration: timedelta = timedelta(minutes=30),
    ) -> None:
        if verification_duration <= timedelta(0):
            raise ValueError("verification_duration must be positive")
        self._store = store
        self._email_sender = email_sender
        self._email_config = email_config
        self._verification_duration = verification_duration
        self._entitlement_store = entitlements
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
        street: str,
        postal_code: str,
        city: str,
        now: datetime,
    ) -> OnlineRegistration:
        registration = OnlineRegistration(
            user_id, display_name, email,
            street=street, postal_code=postal_code, city=city,
        )
        if not all(value.strip() for value in (street, postal_code, city)):
            raise ValueError("billing address is required for registration")
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
        if self._entitlement_store is not None:
            self._entitlement_store.save(entitlement)
        return entitlement

    def deliver_pending_notifications(self, *, now: datetime) -> int:
        """Deliver persisted audit notifications without changing verification."""
        delivered = 0
        for user_id in self._store.pending_notification_user_ids():
            registration = self._store.get(user_id)
            self._notifications.notify_verified(registration)
            self._store.mark_notification_sent(user_id, now=now)
            delivered += 1
        return delivered
