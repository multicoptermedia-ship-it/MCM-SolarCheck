from __future__ import annotations

import pytest

from mcm_solarcheck.services.customer_entry import CustomerEntryGate
from mcm_solarcheck.services.deployment import DeploymentMode


class Production:
    def __init__(self, active: bool) -> None:
        self.active = active
        self.calls = 0

    def require_active(self) -> None:
        self.calls += 1
        if not self.active:
            raise RuntimeError("production inactive")


def test_online_customer_entry_requires_active_production() -> None:
    production = Production(False)
    gate = CustomerEntryGate(DeploymentMode.ONLINE, production)

    with pytest.raises(RuntimeError, match="production inactive"):
        gate.require_customer_entry()

    assert production.calls == 1


def test_online_customer_entry_allows_active_production() -> None:
    production = Production(True)
    gate = CustomerEntryGate(DeploymentMode.ONLINE, production)

    gate.require_customer_entry()

    assert production.calls == 1


def test_offline_customer_entry_is_independent_of_online_production() -> None:
    gate = CustomerEntryGate(DeploymentMode.OFFLINE_DESKTOP)

    gate.require_customer_entry()


def test_online_customer_entry_requires_activation_boundary() -> None:
    with pytest.raises(TypeError, match="production activation"):
        CustomerEntryGate(DeploymentMode.ONLINE)
