"""Application adapter from the online login UI to registration services."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from mcm_solarcheck.services.online_entitlement import OnlineProduct
from mcm_solarcheck.services.online_registration import OnlineRegistrationService
from mcm_solarcheck.services.online_registration_controller import RegistrationRequest


class RegistrationServiceController:
    """Keep time and product policy outside the Qt presentation layer."""

    def __init__(
        self,
        service: OnlineRegistrationService,
        *,
        product: OnlineProduct,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(product, OnlineProduct):
            raise TypeError("product must be an OnlineProduct")
        self._service = service
        self._product = product
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._verified_user_id: str | None = None

    def register(self, request: RegistrationRequest) -> str:
        self._service.register(
            user_id=request.user_id,
            display_name=request.display_name,
            email=request.email,
            street=request.street,
            postal_code=request.postal_code,
            city=request.city,
            now=self._utc_now(),
        )
        return "Bestätigungs-E-Mail wurde gesendet."

    def verify_email_token(self, token: str) -> str:
        entitlement = self._service.verify_and_activate(
            token,
            product=self._product,
            now=self._utc_now(),
        )
        self._verified_user_id = entitlement.user_id
        return "E-Mail-Adresse wurde bestätigt."

    @property
    def verified_user_id(self) -> str | None:
        return self._verified_user_id

    def _utc_now(self) -> datetime:
        value = self._now()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("registration clock must return timezone-aware UTC")
        if value.utcoffset() != timezone.utc.utcoffset(value):
            raise ValueError("registration clock must return UTC")
        return value
