"""Explicit SolarCheck Offline Desktop product boundary."""

from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.customer_entry import CustomerEntryGate
from mcm_solarcheck.services.deployment import DeploymentMode


@dataclass(frozen=True)
class OfflineProduct:
    """Offline product boundary with no dependency on online production state."""

    def require_customer_entry(self) -> None:
        CustomerEntryGate(DeploymentMode.OFFLINE_DESKTOP).require_customer_entry()
