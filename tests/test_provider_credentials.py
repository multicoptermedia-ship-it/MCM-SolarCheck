from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.environment_secret import EnvironmentSecretResolver
from mcm_solarcheck.services.merchant_account import (
    MerchantAccount,
    MerchantAccountKind,
)
from mcm_solarcheck.services.payment import OnlinePayment, PaymentAmount
from mcm_solarcheck.services.payment_methods import PaymentMethod
from mcm_solarcheck.services.provider_credentials import (
    MerchantProviderAdapter,
    ProviderCredential,
    ProviderCredentialResolver,
    PaymentBoundProviderAdapter,
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


class LeakingProviderClient:
    def call(
        self,
        *,
        credential,
        operation,
        payload,
        idempotency_key,
    ):
        return credential.value


def test_provider_adapter_rejects_credential_as_provider_reference() -> None:
    adapter = MerchantProviderAdapter(
        ProviderCredentialResolver(
            EnvironmentSecretResolver(
                {"PAYPAL_MAIN": "super-secret-runtime-value"}
            )
        ),
        LeakingProviderClient(),
    )

    with pytest.raises(ValueError, match="must not expose credential"):
        adapter.call(
            merchant(),
            operation="authorize",
            payload={"amount": 12900},
            idempotency_key="payment:payment-a:authorize",
        )


class MerchantHistory:
    def __init__(self, accounts):
        self.accounts = {
            (account.account_id, account.version): account
            for account in accounts
        }
        self.requests = []

    def get(self, account_id, version):
        self.requests.append((account_id, version))
        return self.accounts[(account_id, version)]


def bound_payment(*, version=1, provider_id="provider-a") -> OnlinePayment:
    return OnlinePayment(
        "payment-bound",
        "user-a",
        "project-a",
        "job-bound",
        PaymentAmount(12900, "EUR"),
        method=PaymentMethod.PAYPAL,
        merchant_account_id="paypal-main",
        merchant_account_version=version,
        provider_id=provider_id,
    )


def test_payment_bound_adapter_uses_historical_account_version() -> None:
    old = merchant()
    current = old.supersede(
        display_reference="new-masked-reference",
        credential_key="env:PAYPAL_NEW",
    )
    history = MerchantHistory([old, current])
    client = RecordingProviderClient()
    adapter = PaymentBoundProviderAdapter(
        history,
        MerchantProviderAdapter(
            ProviderCredentialResolver(
                EnvironmentSecretResolver(
                    {
                        "PAYPAL_MAIN": "old-runtime-secret",
                        "PAYPAL_NEW": "new-runtime-secret",
                    }
                )
            ),
            client,
        ),
    )

    adapter.call(
        bound_payment(version=1),
        provider_id="provider-a",
        operation="capture",
        payload={"provider_reference": "provider-auth-a"},
        idempotency_key="payment:payment-bound:capture",
    )

    assert history.requests == [("paypal-main", 1)]
    assert client.calls[0][0].value == "old-runtime-secret"


def test_payment_bound_adapter_rejects_provider_switch_before_secret_resolution() -> None:
    history = MerchantHistory([merchant()])
    client = RecordingProviderClient()
    adapter = PaymentBoundProviderAdapter(
        history,
        MerchantProviderAdapter(
            ProviderCredentialResolver(
                EnvironmentSecretResolver(
                    {"PAYPAL_MAIN": "super-secret-runtime-value"}
                )
            ),
            client,
        ),
    )

    with pytest.raises(ValueError, match="provider snapshot mismatch"):
        adapter.call(
            bound_payment(),
            provider_id="provider-b",
            operation="authorize",
            payload={"amount": 12900},
            idempotency_key="payment:payment-bound:authorize",
        )

    assert history.requests == []
    assert client.calls == []
