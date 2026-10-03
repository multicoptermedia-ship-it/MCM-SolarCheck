"""Deployment-aware gate for customer-facing SolarCheck entry."""

from __future__ import annotations

from typing import Protocol

from mcm_solarcheck.services.deployment import DeploymentMode


class ProductionActivation(Protocol):
    def require_active(self) -> None:
        ...


class CustomerEntryGate:
    """Require production activation for online customers, never for offline desktop."""

    def __init__(
        self,
        deployment: DeploymentMode,
        production: ProductionActivation | None = None,
    ) -> None:
        if not isinstance(deployment, DeploymentMode):
            raise ValueError("deployment must be a DeploymentMode")
        if deployment is DeploymentMode.ONLINE:
            if not callable(getattr(production, "require_active", None)):
                raise TypeError("online deployment requires production activation")
        self._deployment = deployment
        self._production = production

    def require_customer_entry(self) -> None:
        if self._deployment is DeploymentMode.ONLINE:
            self._production.require_active()
