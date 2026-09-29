"""Server-owned payment pricing with optional FlightPlan voucher."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from mcm_solarcheck.services.payment import OnlinePayment, OnlinePaymentStore, PaymentAmount
from mcm_solarcheck.services.voucher import FlightPlanVoucher, discounted_amount
from mcm_solarcheck.services.voucher_admin import FlightPlanVoucherPolicy


class VoucherRedemptionStore(Protocol):
    def redeem(
        self,
        code: str,
        payment_id: str,
        *,
        discount_percent: int,
        now: datetime,
    ) -> FlightPlanVoucher:
        ...


class PaymentPricingService:
    """Fix the payable amount before any provider authorization occurs."""

    def __init__(
        self,
        payments: OnlinePaymentStore,
        vouchers: VoucherRedemptionStore,
        voucher_policy: FlightPlanVoucherPolicy,
    ) -> None:
        self._payments = payments
        self._vouchers = vouchers
        self._voucher_policy = voucher_policy

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
    ) -> OnlinePayment | None:
        amount = base_amount
        if voucher_code is not None:
            voucher = self._vouchers.redeem(
                voucher_code,
                payment_id,
                discount_percent=self._voucher_policy.discount_percent,
                now=now,
            )
            amount = discounted_amount(
                base_amount,
                discount_percent=voucher.redeemed_discount_percent,
            )
            if amount is None:
                return None

        payment = OnlinePayment(
            payment_id,
            user_id,
            project_id,
            job_id,
            amount,
        )
        self._payments.create(payment)
        return payment
