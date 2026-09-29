"""Administrative creation boundary for FlightPlan vouchers."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from mcm_solarcheck.services.payment import PaymentAmount
from mcm_solarcheck.services.voucher import FlightPlanVoucher


class VoucherAdminStore(Protocol):
    def create(self, voucher: FlightPlanVoucher) -> None:
        ...


class FlightPlanVoucherAdminService:
    """Create voucher value and validity from trusted admin input."""

    def __init__(self, store: VoucherAdminStore) -> None:
        self._store = store

    def create(
        self,
        code: str,
        *,
        value_minor_units: int,
        currency: str,
        valid_from: datetime,
        valid_until: datetime,
    ) -> FlightPlanVoucher:
        voucher = FlightPlanVoucher(
            code,
            PaymentAmount(value_minor_units, currency),
            valid_from,
            valid_until,
        )
        self._store.create(voucher)
        return voucher
