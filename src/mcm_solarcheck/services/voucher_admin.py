"""Administrative configuration boundary for FlightPlan vouchers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from mcm_solarcheck.services.voucher import FlightPlanVoucher, _require_discount_percent


class VoucherAdminStore(Protocol):
    def create(self, voucher: FlightPlanVoucher) -> None:
        ...


@dataclass(frozen=True)
class FlightPlanVoucherPolicy:
    """Global discount policy controlled by SolarCheck administration."""

    discount_percent: int = 10

    def __post_init__(self) -> None:
        _require_discount_percent(self.discount_percent)


class FlightPlanVoucherAdminService:
    """Create voucher codes independently of the globally configured discount."""

    def __init__(self, store: VoucherAdminStore) -> None:
        self._store = store

    def create(
        self,
        code: str,
        *,
        valid_from: datetime,
        valid_until: datetime,
    ) -> FlightPlanVoucher:
        voucher = FlightPlanVoucher(code, valid_from, valid_until)
        self._store.create(voucher)
        return voucher
