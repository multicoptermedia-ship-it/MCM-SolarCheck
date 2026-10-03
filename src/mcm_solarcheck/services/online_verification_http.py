"""Transport-neutral HTTP boundary for online email verification."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Protocol

from mcm_solarcheck.services.online_entitlement import OnlineProduct


class RegistrationVerification(Protocol):
    def verify_and_activate(self, token: str, *, product: OnlineProduct, now: datetime):
        ...


@dataclass(frozen=True)
class VerificationHttpResult:
    status_code: int
    message: str
    user_id: str | None = None


class EmailVerificationEndpoint:
    """Map an HTTP verification request onto the authoritative registration service."""

    def __init__(
        self,
        registration: RegistrationVerification,
        *,
        product: OnlineProduct = OnlineProduct.TRIAL,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._registration = registration
        self._product = product
        self._now = now or (lambda: datetime.now(timezone.utc))

    def verify(self, token: str | None) -> VerificationHttpResult:
        if token is None or not token.strip():
            return VerificationHttpResult(400, "verification token is required")
        try:
            entitlement = self._registration.verify_and_activate(
                token,
                product=self._product,
                now=self._utc_now(),
            )
        except (ValueError, PermissionError):
            return VerificationHttpResult(400, "verification token is invalid or expired")
        return VerificationHttpResult(
            200,
            "E-Mail-Adresse wurde bestätigt.",
            entitlement.user_id,
        )

    def _utc_now(self) -> datetime:
        value = self._now()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("verification clock must return timezone-aware UTC")
        if value.utcoffset() != timezone.utc.utcoffset(value):
            raise ValueError("verification clock must return UTC")
        return value
