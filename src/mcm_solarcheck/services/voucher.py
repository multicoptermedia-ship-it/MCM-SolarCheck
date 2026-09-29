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
    """One-time voucher whose monetary value is configured by SolarCheck admin."""

    code: str
    value: PaymentAmount
    valid_from: datetime
    valid_until: datetime
    redeemed_payment_id: str | None = None
    redeemed_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code.strip():
            raise ValueError("voucher code must be non-empty")
        object.__setattr__(self, "code", self.code.strip())
        _require_utc(self.valid_from, "valid_from")
        _require_utc(self.valid_until, "valid_until")
        if self.valid_until <= self.valid_from:
            raise ValueError("valid_until must be after valid_from")
        if (self.redeemed_payment_id is None) != (self.redeemed_at is None):
            raise ValueError("voucher redemption identity and time must be set together")
        if self.redeemed_at is not None:
            _require_utc(self.redeemed_at, "redeemed_at")

    @property
    def redeemed(self) -> bool:
        return self.redeemed_payment_id is not None

    def redeem(self, payment_id: str, *, now: datetime) -> "FlightPlanVoucher":
        _require_utc(now, "now")
        if self.redeemed:
            raise ValueError("voucher already redeemed")
        if now < self.valid_from or now >= self.valid_until:
            raise ValueError("voucher is not valid at redemption time")
        if not isinstance(payment_id, str) or not payment_id.strip():
            raise ValueError("payment_id must be non-empty")
        return FlightPlanVoucher(
            self.code,
            self.value,
            self.valid_from,
            self.valid_until,
            payment_id.strip(),
            now,
        )


def discounted_amount(amount: PaymentAmount, voucher: FlightPlanVoucher) -> PaymentAmount | None:
    """Apply admin-configured voucher value without ever producing a negative charge."""
    if amount.currency != voucher.value.currency:
        raise ValueError("voucher currency does not match payment currency")
    remaining = max(0, amount.minor_units - voucher.value.minor_units)
    if remaining == 0:
        return None
    return PaymentAmount(remaining, amount.currency)
