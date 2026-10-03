from __future__ import annotations

import pytest

from mcm_solarcheck.services.online_activation import (
    OnlineActivationState,
    OnlineProductionActivation,
)


class Readiness:
    def __init__(self, ready: bool) -> None:
        self.ready = ready
        self.calls = 0

    def require_production_ready(self) -> None:
        self.calls += 1
        if not self.ready:
            raise RuntimeError("deployment is not ready")


def test_online_production_starts_inactive() -> None:
    activation = OnlineProductionActivation(Readiness(True))

    assert activation.state is OnlineActivationState.INACTIVE
    assert activation.active is False
    with pytest.raises(RuntimeError, match="production operation is not active"):
        activation.require_active()


def test_online_production_activates_only_after_readiness_passes() -> None:
    readiness = Readiness(True)
    activation = OnlineProductionActivation(readiness)

    activation.activate()

    assert readiness.calls == 1
    assert activation.state is OnlineActivationState.ACTIVE
    assert activation.active is True
    activation.require_active()


def test_failed_readiness_keeps_online_production_inactive() -> None:
    readiness = Readiness(False)
    activation = OnlineProductionActivation(readiness)

    with pytest.raises(RuntimeError, match="deployment is not ready"):
        activation.activate()

    assert readiness.calls == 1
    assert activation.state is OnlineActivationState.INACTIVE
    assert activation.active is False


def test_online_activation_requires_explicit_readiness_boundary() -> None:
    with pytest.raises(TypeError, match=r"require_production_ready\(\)"):
        OnlineProductionActivation(object())  # type: ignore[arg-type]
