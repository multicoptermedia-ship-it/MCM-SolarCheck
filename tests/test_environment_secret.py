from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.environment_secret import (
    EnvironmentSecretResolver,
)


def test_environment_secret_resolver_returns_runtime_value() -> None:
    resolver = EnvironmentSecretResolver(
        {"PAYPAL_MAIN": "runtime-secret-value"}
    )

    assert resolver.resolve("env:PAYPAL_MAIN") == "runtime-secret-value"


def test_environment_secret_resolver_rejects_other_reference_schemes() -> None:
    resolver = EnvironmentSecretResolver({})

    with pytest.raises(ValueError, match="env: reference"):
        resolver.resolve("secret:payments/paypal/main")


def test_environment_secret_resolver_does_not_accept_missing_or_empty_secret() -> None:
    resolver = EnvironmentSecretResolver({"EMPTY": ""})

    with pytest.raises(KeyError):
        resolver.resolve("env:MISSING")
    with pytest.raises(ValueError, match="non-empty"):
        resolver.resolve("env:EMPTY")
