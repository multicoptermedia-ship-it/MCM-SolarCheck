"""Deployment-aware gate for customer-facing SolarCheck entry."""

from __future__ import annotations

from typing import Protocol

from mcm_solarcheck.services.deployment import DeploymentMode


class ProductionActivation(Protocol):
    def require_active(self) -> None:
        ...


class ProductEntitlements(Protocol):
    def require_active(self, user_id: str):
        ...


class CustomerEntryGate:
    """Require production activation and identified entitlement for online customers."""

    def __init__(
        self,
        deployment: DeploymentMode,
        production: ProductionActivation | None = None,
        *,
        entitlements: ProductEntitlements | None = None,
        user_id: str | None = None,
    ) -> None:
        if not isinstance(deployment, DeploymentMode):
            raise ValueError("deployment must be a DeploymentMode")
        if deployment is DeploymentMode.ONLINE:
            if not callable(getattr(production, "require_active", None)):
                raise TypeError("online deployment requires production activation")
            if (entitlements is None) != (user_id is None):
                raise ValueError("online entitlement and user identity must be supplied together")
            if entitlements is not None and not callable(
                getattr(entitlements, "require_active", None)
            ):
                raise TypeError("online entitlements must provide require_active()")
            if user_id is not None and not user_id.strip():
                raise ValueError("online user identity must be non-empty")
        self._deployment = deployment
        self._production = production
        self._entitlements = entitlements
        self._user_id = user_id

    def require_customer_entry(self) -> None:
        if self._deployment is DeploymentMode.ONLINE:
            self._production.require_active()
            if self._entitlements is not None:
                self._entitlements.require_active(self._user_id)
