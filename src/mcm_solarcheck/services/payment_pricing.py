"""Server-owned payment pricing with optional FlightPlan voucher."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from mcm_solarcheck.services.payment import (
    OnlinePayment,
    OnlinePaymentStore,
    PaymentAmount,
    PaymentStatus,
)
from mcm_solarcheck.services.voucher import FlightPlanVoucher, discounted_amount
from mcm_solarcheck.services.voucher_admin import FlightPlanVoucherPolicy


class VoucherRedemptionStore(Protocol):
    def get(self, code: str) -> FlightPlanVoucher:
        ...

    def redeem(
        self,
        code: str,
        payment_id: str,
        *,
        discount_percent: int,
        now: datetime,
    ) -> FlightPlanVoucher:
        ...


class AtomicPricedPaymentStore(Protocol):
    def create_with_voucher(
        self,
        payment: OnlinePayment,
        *,
        voucher_code: str,
        discount_percent: int,
        now: datetime,
    ) -> FlightPlanVoucher:
        ...


class VoucherPolicyStore(Protocol):
    def current(self) -> FlightPlanVoucherPolicy:
        ...


class PaymentPricingService:
    """Fix the payable amount before any provider authorization occurs."""

    def __init__(
        self,
        payments: OnlinePaymentStore,
        vouchers: VoucherRedemptionStore,
        voucher_policy: FlightPlanVoucherPolicy | VoucherPolicyStore,
        atomic_store: AtomicPricedPaymentStore | None = None,
    ) -> None:
        self._payments = payments
        self._vouchers = vouchers
        self._voucher_policy = voucher_policy
        self._atomic_store = atomic_store

    def create_payment(
        self,
        payment_id: str,
        *,
        user_id: str,
        project_id: str,
        job_id: str,
        base_amount: PaymentAmount,
        now: datetime,
        voucher_code: str | None = None,
    ) -> OnlinePayment:
        amount = base_amount
        discount_percent: int | None = None
        if voucher_code is not None:
            policy = (
                self._voucher_policy.current()
                if hasattr(self._voucher_policy, "current")
                else self._voucher_policy
            )
            if not policy.active:
                raise ValueError("voucher policy is inactive")
            discount_percent = policy.discount_percent
            if self._atomic_store is None:
                raise ValueError(
                    "voucher payment requires atomic payment persistence"
                )
            voucher = self._vouchers.get(voucher_code)
            voucher.redeem(
                payment_id,
                discount_percent=discount_percent,
                now=now,
            )
            amount = discounted_amount(
                base_amount,
                discount_percent=discount_percent,
            )
        payment = OnlinePayment(
            payment_id,
            user_id,
            project_id,
            job_id,
            amount,
            PaymentStatus.SETTLED if amount is None else PaymentStatus.CREATED,
        )
        if voucher_code is not None:
            self._atomic_store.create_with_voucher(
                payment,
                voucher_code=voucher_code,
                discount_percent=discount_percent,
                now=now,
            )
        else:
            self._payments.create(payment)
        return payment
