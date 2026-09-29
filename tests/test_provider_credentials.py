from __future__ import annotations

from mcm_solarcheck.infrastructure.environment_secret import EnvironmentSecretResolver
from mcm_solarcheck.services.merchant_account import (
    MerchantAccount,
    MerchantAccountKind,
)
from mcm_solarcheck.services.provider_credentials import (
    MerchantProviderAdapter,
    ProviderCredential,
    ProviderCredentialResolver,
)


class RecordingProviderClient:
    def __init__(self) -> None:
        self.calls = []

    def call(
        self,
        *,
        credential,
        operation,
        payload,
        idempotency_key,
    ):
        self.calls.append(
            (credential, operation, payload, idempotency_key)
        )
        return "provider-reference-a"


def merchant() -> MerchantAccount:
    return MerchantAccount(
        "paypal-main",
        "provider-a",
        MerchantAccountKind.PAYPAL,
        "masked-reference",
        credential_key="env:PAYPAL_MAIN",
    )


def test_provider_adapter_resolves_secret_only_for_runtime_call() -> None:
    secrets = EnvironmentSecretResolver(
        {"PAYPAL_MAIN": "super-secret-runtime-value"}
    )
    client = RecordingProviderClient()
    adapter = MerchantProviderAdapter(
        ProviderCredentialResolver(secrets),
        client,
    )

    result = adapter.call(
        merchant(),
        operation="authorize",
        payload={"amount": 12900},
        idempotency_key="payment:payment-a:authorize",
    )

    assert result == "provider-reference-a"
    credential = client.calls[0][0]
    assert isinstance(credential, ProviderCredential)
    assert credential.value == "super-secret-runtime-value"
    assert merchant().credential_key == "env:PAYPAL_MAIN"


def test_provider_credential_masks_string_and_repr() -> None:
    credential = ProviderCredential("super-secret-runtime-value")

    assert str(credential) == "<redacted>"
    assert repr(credential) == "ProviderCredential(<redacted>)"
    assert "super-secret-runtime-value" not in str(credential)
    assert "super-secret-runtime-value" not in repr(credential)
