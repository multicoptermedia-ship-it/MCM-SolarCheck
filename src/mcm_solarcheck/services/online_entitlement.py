"""Server-owned online product entitlement boundary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from mcm_solarcheck.services.registration import OnlineRegistration, RegistrationStatus


class OnlineProduct(str, Enum):
    TRIAL = "trial"
    FULL = "full"


@dataclass(frozen=True)
class OnlineEntitlement:
    """Access grant kept separate from registration identity."""

    user_id: str
    product: OnlineProduct
    active: bool = False


class OnlineEntitlementStore(Protocol):
    """Provider-neutral persistence boundary for online product access."""

    def save(self, entitlement: OnlineEntitlement) -> None:
        ...

    def get(self, user_id: str) -> OnlineEntitlement:
        ...

    def require_active(self, user_id: str) -> OnlineEntitlement:
        ...


class OnlineEntitlementService:
    """Activate online use only for a verified registration identity."""

    def activate(
        self,
        entitlement: OnlineEntitlement,
        registration: OnlineRegistration,
    ) -> OnlineEntitlement:
        if entitlement.user_id != registration.user_id:
            raise PermissionError("entitlement identity does not match registration")
        if registration.status is not RegistrationStatus.VERIFIED:
            raise PermissionError("verified email identity required")
        if entitlement.active:
            return entitlement
        return OnlineEntitlement(
            user_id=entitlement.user_id,
            product=entitlement.product,
            active=True,
        )
