"""Provider-neutral authentication boundary for SolarCheck Online."""

from __future__ import annotations

from typing import Protocol

from mcm_solarcheck.services.registration import RegistrationStatus


class RegistrationIdentityStore(Protocol):
    def get(self, user_id: str):
        ...


class OnlineAuthenticationService:
    """Resolve an authenticated customer only from an already verified identity.

    Credential proof is intentionally supplied by a later authentication provider;
    this service owns the invariant that unverified registrations cannot enter the
    authenticated SolarCheck Online flow.
    """

    def __init__(self, registrations: RegistrationIdentityStore) -> None:
        self._registrations = registrations

    def require_verified_identity(self, user_id: str) -> str:
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user identity must be non-empty")
        try:
            registration = self._registrations.get(user_id)
        except KeyError as exc:
            raise PermissionError("online identity is not registered") from exc
        if registration.status is not RegistrationStatus.VERIFIED:
            raise PermissionError("online identity is not verified")
        return registration.user_id
