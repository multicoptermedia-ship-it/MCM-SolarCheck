"""Server-owned FlightPlan voucher rules for SolarCheck Online."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from mcm_solarcheck.services.payment import PaymentAmount


def _require_utc(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError(f"{name} must be timezone-aware UTC")


@dataclass(frozen=True)
class FlightPlanVoucher:
    """One-time FlightPlan voucher with validity and redemption evidence."""

    code: str
    valid_from: datetime
    valid_until: datetime
    redeemed_payment_id: str | None = None
    redeemed_at: datetime | None = None
    redeemed_discount_percent: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code.strip():
            raise ValueError("voucher code must be non-empty")
        object.__setattr__(self, "code", self.code.strip())
        _require_utc(self.valid_from, "valid_from")
        _require_utc(self.valid_until, "valid_until")
        if self.valid_until <= self.valid_from:
            raise ValueError("valid_until must be after valid_from")
        redemption_values = (
            self.redeemed_payment_id,
            self.redeemed_at,
            self.redeemed_discount_percent,
        )
        if any(value is not None for value in redemption_values) and not all(
            value is not None for value in redemption_values
        ):
            raise ValueError("voucher redemption evidence must be set together")
        if self.redeemed_at is not None:
            _require_utc(self.redeemed_at, "redeemed_at")
        if self.redeemed_discount_percent is not None:
            _require_discount_percent(self.redeemed_discount_percent)

    @property
    def redeemed(self) -> bool:
        return self.redeemed_payment_id is not None

    def redeem(
        self, payment_id: str, *, discount_percent: int, now: datetime
    ) -> "FlightPlanVoucher":
        _require_utc(now, "now")
        _require_discount_percent(discount_percent)
        if self.redeemed:
            raise ValueError("voucher already redeemed")
        if now < self.valid_from or now >= self.valid_until:
            raise ValueError("voucher is not valid at redemption time")
        if not isinstance(payment_id, str) or not payment_id.strip():
            raise ValueError("payment_id must be non-empty")
        return FlightPlanVoucher(
            self.code,
            self.valid_from,
            self.valid_until,
            payment_id.strip(),
            now,
            discount_percent,
        )


def _require_discount_percent(value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 100:
        raise ValueError("discount_percent must be an integer from 1 to 100")


def discounted_amount(
    amount: PaymentAmount, *, discount_percent: int
) -> PaymentAmount | None:
    """Apply a percentage discount using integer arithmetic."""
    _require_discount_percent(discount_percent)
    discount = amount.minor_units * discount_percent // 100
    remaining = amount.minor_units - discount
    if remaining == 0:
        return None
    return PaymentAmount(remaining, amount.currency)
