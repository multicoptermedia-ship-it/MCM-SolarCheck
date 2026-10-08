"""Fail-closed activation boundary for customer-facing SolarCheck Online."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class ProductionReadiness(Protocol):
    def require_production_ready(self) -> None:
        ...


class OnlineActivationState(str, Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"


@dataclass
class OnlineProductionActivation:
    """Keep customer-facing online operation disabled until readiness succeeds."""

    readiness: ProductionReadiness
    _state: OnlineActivationState = OnlineActivationState.INACTIVE

    def __post_init__(self) -> None:
        if not callable(getattr(self.readiness, "require_production_ready", None)):
            raise TypeError("readiness must provide require_production_ready()")

    @property
    def state(self) -> OnlineActivationState:
        return self._state

    @property
    def active(self) -> bool:
        return self._state is OnlineActivationState.ACTIVE

    def activate(self) -> None:
        """Activate only after the complete production-readiness gate passes."""
        self.readiness.require_production_ready()
        self._state = OnlineActivationState.ACTIVE

    def require_active(self) -> None:
        """Fail closed at customer-facing entry boundaries."""
        if not self.active:
            raise RuntimeError("SolarCheck Online production operation is not active")
