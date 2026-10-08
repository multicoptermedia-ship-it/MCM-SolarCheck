"""Explicit SolarCheck Online product composition boundary."""

from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.customer_entry import CustomerEntryGate
from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.online_composition import OnlineServices


@dataclass(frozen=True)
class OnlineProduct:
    services: OnlineServices

    @classmethod
    def compose(cls, services: OnlineServices) -> "OnlineProduct":
        return cls(services=services)

    def require_customer_entry(self, user_id: str | None = None) -> None:
        CustomerEntryGate(
            DeploymentMode.ONLINE,
            self.services.production,
            entitlements=(self.services.entitlements if user_id is not None else None),
            user_id=user_id,
        ).require_customer_entry()
