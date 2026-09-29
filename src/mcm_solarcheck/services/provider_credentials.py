"""Resolve merchant credentials only at the external provider boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from mcm_solarcheck.services.merchant_account import MerchantAccount
from mcm_solarcheck.services.secret_resolver import SecretResolver


@dataclass(frozen=True)
class ProviderCredential:
    """Ephemeral credential material; never persist this object."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("provider credential must be non-empty")

    def __repr__(self) -> str:
        return "ProviderCredential(<redacted>)"

    def __str__(self) -> str:
        return "<redacted>"


class ProviderCredentialResolver:
    def __init__(self, secrets: SecretResolver) -> None:
        self._secrets = secrets

    def resolve(self, account: MerchantAccount) -> ProviderCredential:
        if account.credential_key is None:
            raise ValueError("merchant account has no credential reference")
        return ProviderCredential(self._secrets.resolve(account.credential_key))


class CredentialAwareProviderClient(Protocol):
    def call(
        self,
        *,
        credential: ProviderCredential,
        operation: str,
        payload: object,
        idempotency_key: str,
    ) -> str | None:
        ...


class MerchantProviderAdapter:
    """Resolve credentials immediately before delegating to a provider client."""

    def __init__(
        self,
        credentials: ProviderCredentialResolver,
        client: CredentialAwareProviderClient,
    ) -> None:
        self._credentials = credentials
        self._client = client

    def call(
        self,
        account: MerchantAccount,
        *,
        operation: str,
        payload: object,
        idempotency_key: str,
    ) -> str | None:
        credential = self._credentials.resolve(account)
        return self._client.call(
            credential=credential,
            operation=operation,
            payload=payload,
            idempotency_key=idempotency_key,
        )
