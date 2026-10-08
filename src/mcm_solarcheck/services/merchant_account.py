"""Versioned merchant account configuration for payment providers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


_CREDENTIAL_REFERENCE_PREFIXES = ("env:", "secret:")


def _validate_credential_reference(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("credential_key must be non-empty when configured")
    reference = value.strip()
    if not reference.startswith(_CREDENTIAL_REFERENCE_PREFIXES):
        raise ValueError(
            "credential_key must be a secret reference, not credential material"
        )
    if ":" not in reference or not reference.split(":", 1)[1].strip():
        raise ValueError("credential_key secret reference must include a key")
    return reference


class MerchantAccountKind(str, Enum):
    BANK = "bank"
    PAYPAL = "paypal"
    CARD_PROCESSOR = "card_processor"


@dataclass(frozen=True)
class MerchantAccount:
    account_id: str
    provider_id: str
    kind: MerchantAccountKind
    display_reference: str
    version: int = 1
    active: bool = True
    credential_key: str | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("account_id", self.account_id),
            ("provider_id", self.provider_id),
            ("display_reference", self.display_reference),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if not isinstance(self.version, int) or isinstance(self.version, bool):
            raise ValueError("version must be an integer")
        if self.version <= 0:
            raise ValueError("version must be positive")
        credential_reference = _validate_credential_reference(self.credential_key)
        object.__setattr__(self, "credential_key", credential_reference)

    def deactivate(self) -> "MerchantAccount":
        if not self.active:
            raise ValueError("merchant account is already inactive")
        return MerchantAccount(
            self.account_id,
            self.provider_id,
            self.kind,
            self.display_reference,
            self.version + 1,
            False,
            self.credential_key,
        )

    def reactivate(self) -> "MerchantAccount":
        if self.active:
            raise ValueError("merchant account is already active")
        return MerchantAccount(
            self.account_id,
            self.provider_id,
            self.kind,
            self.display_reference,
            self.version + 1,
            True,
            self.credential_key,
        )

    def supersede(
        self,
        *,
        display_reference: str,
        credential_key: str | None = None,
    ) -> "MerchantAccount":
        return MerchantAccount(
            self.account_id,
            self.provider_id,
            self.kind,
            display_reference,
            self.version + 1,
            True,
            credential_key,
        )



class MerchantAccountPersistence(Protocol):
    """Provider-neutral persistence for versioned merchant configuration.

    Historical versions remain addressable because existing payments are bound
    to the exact merchant-account version selected at checkout.
    """

    def save(self, account: MerchantAccount) -> None:
        ...

    def get(self, account_id: str, version: int) -> MerchantAccount:
        ...

    def current(self, account_id: str) -> MerchantAccount:
        ...

    def is_configured(self) -> bool:
        ...
