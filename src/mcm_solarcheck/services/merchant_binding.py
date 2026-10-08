"""Bind the current merchant account version to new payments."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from mcm_solarcheck.services.merchant_account import (
    MerchantAccount,
    MerchantAccountKind,
)
from mcm_solarcheck.services.payment_methods import PaymentMethod
from mcm_solarcheck.services.payment import OnlinePayment


class MerchantAccountStore(Protocol):
    def current(self, account_id: str) -> MerchantAccount:
        ...


class MerchantAccountBindingService:
    def __init__(self, accounts: MerchantAccountStore) -> None:
        self._accounts = accounts

    def bind(
        self, payment: OnlinePayment, account_id: str, *, provider_id: str | None = None
    ) -> OnlinePayment:
        if payment.merchant_account_id is not None:
            raise ValueError("payment already has merchant account snapshot")

        account = self._accounts.current(account_id)
        expected_kind = {
            PaymentMethod.SEPA_DIRECT_DEBIT: MerchantAccountKind.BANK,
            PaymentMethod.PAYPAL: MerchantAccountKind.PAYPAL,
            PaymentMethod.CARD: MerchantAccountKind.CARD_PROCESSOR,
        }.get(payment.method)
        if expected_kind is None:
            raise ValueError("payment method is required for merchant binding")
        if account.kind is not expected_kind:
            raise ValueError("merchant account kind does not match payment method")
        if payment.provider_id is not None:
            raise ValueError("payment already has provider snapshot")
        if provider_id is not None:
            if not isinstance(provider_id, str) or not provider_id.strip():
                raise ValueError("provider_id must be non-empty when configured")
            if account.provider_id != provider_id.strip():
                raise ValueError("merchant account provider mismatch")

        return replace(
            payment,
            merchant_account_id=account.account_id,
            merchant_account_version=account.version,
            provider_id=account.provider_id,
        )
