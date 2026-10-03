from __future__ import annotations

import pytest

from mcm_solarcheck.services.customer_entry import CustomerEntryGate
from mcm_solarcheck.services.deployment import DeploymentMode


class Production:
    def __init__(self) -> None:
        self.calls = 0

    def require_active(self) -> None:
        self.calls += 1


class Entitlements:
    def __init__(self) -> None:
        self.users = []

    def require_active(self, user_id: str) -> None:
        self.users.append(user_id)


def test_identified_online_entry_requires_production_then_user_entitlement() -> None:
    production = Production()
    entitlements = Entitlements()
    gate = CustomerEntryGate(
        DeploymentMode.ONLINE,
        production,
        entitlements=entitlements,
        user_id="user-1",
    )

    gate.require_customer_entry()

    assert production.calls == 1
    assert entitlements.users == ["user-1"]


def test_online_entry_rejects_partial_identity_context() -> None:
    with pytest.raises(ValueError, match="supplied together"):
        CustomerEntryGate(
            DeploymentMode.ONLINE,
            Production(),
            user_id="user-1",
        )


def test_offline_entry_does_not_require_online_identity() -> None:
    gate = CustomerEntryGate(DeploymentMode.OFFLINE_DESKTOP)

    gate.require_customer_entry()
