"""Bind the current merchant account version to new payments."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from mcm_solarcheck.services.merchant_account import MerchantAccount
from mcm_solarcheck.services.payment import OnlinePayment


class MerchantAccountStore(Protocol):
    def current(self, account_id: str) -> MerchantAccount:
        ...


class MerchantAccountBindingService:
    def __init__(self, accounts: MerchantAccountStore) -> None:
        self._accounts = accounts

    def bind(self, payment: OnlinePayment, account_id: str) -> OnlinePayment:
        if payment.merchant_account_id is not None:
            raise ValueError("payment already has merchant account snapshot")

        account = self._accounts.current(account_id)
        return replace(
            payment,
            merchant_account_id=account.account_id,
            merchant_account_version=account.version,
        )
