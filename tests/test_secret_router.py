from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.environment_secret import EnvironmentSecretResolver
from mcm_solarcheck.infrastructure.secret_router import SecretResolverRouter


class RecordingSecretResolver:
    def __init__(self) -> None:
        self.references: list[str] = []

    def resolve(self, reference: str) -> str:
        self.references.append(reference)
        return "vault-runtime-secret"


def test_secret_router_delegates_by_reference_scheme() -> None:
    vault = RecordingSecretResolver()
    router = SecretResolverRouter({
        "env": EnvironmentSecretResolver({"PAYPAL_MAIN": "env-secret"}),
        "secret": vault,
    })

    assert router.resolve("env:PAYPAL_MAIN") == "env-secret"
    assert router.resolve("secret:payments/paypal/main") == "vault-runtime-secret"
    assert vault.references == ["secret:payments/paypal/main"]


def test_secret_router_rejects_unknown_or_unqualified_reference() -> None:
    router = SecretResolverRouter({
        "env": EnvironmentSecretResolver({"PAYPAL_MAIN": "env-secret"})
    })

    with pytest.raises(ValueError, match="unsupported"):
        router.resolve("secret:payments/paypal/main")
    with pytest.raises(ValueError, match="scheme"):
        router.resolve("PAYPAL_MAIN")
