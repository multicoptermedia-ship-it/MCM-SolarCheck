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
    """Versioned global discount policy controlled by SolarCheck administration."""

    discount_percent: int = 10
    version: int = 1
    active: bool = True

    def __post_init__(self) -> None:
        _require_discount_percent(self.discount_percent)
        if self.discount_percent != 10:
            raise ValueError("FlightPlan voucher discount must be 10 percent")
        if not isinstance(self.version, int) or isinstance(self.version, bool):
            raise ValueError("version must be an integer")
        if self.version <= 0:
            raise ValueError("version must be positive")
        if not isinstance(self.active, bool):
            raise ValueError("active must be boolean")

    def supersede(self) -> "FlightPlanVoucherPolicy":
        return FlightPlanVoucherPolicy(
            10,
            self.version + 1,
            True,
        )

    def deactivate(self) -> "FlightPlanVoucherPolicy":
        if not self.active:
            raise ValueError("voucher policy is already inactive")
        return FlightPlanVoucherPolicy(
            self.discount_percent,
            self.version + 1,
            False,
        )


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



class FlightPlanVoucherPolicyPersistence(Protocol):
    """Append-only persistence for versioned voucher policy history."""

    def bootstrap_default(self) -> FlightPlanVoucherPolicy:
        ...

    def save(self, policy: FlightPlanVoucherPolicy) -> None:
        ...

    def get(self, version: int) -> FlightPlanVoucherPolicy:
        ...

    def current(self) -> FlightPlanVoucherPolicy:
        ...
