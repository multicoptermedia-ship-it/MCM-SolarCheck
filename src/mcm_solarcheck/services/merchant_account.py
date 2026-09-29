"""Versioned merchant account configuration for payment providers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


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
        if self.credential_key is not None and not self.credential_key.strip():
            raise ValueError("credential_key must be non-empty when configured")

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
