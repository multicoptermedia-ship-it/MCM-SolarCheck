"""One-time introductory offer policy for registered SolarCheck customers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from mcm_solarcheck.services.payment import PaymentAmount


@dataclass(frozen=True)
class IntroductoryOfferPolicy:
    amount: PaymentAmount = PaymentAmount(5900, "EUR")
    valid_until: datetime = datetime(2027, 1, 1, tzinfo=timezone.utc)
    version: int = 1

    def __post_init__(self) -> None:
        if self.amount != PaymentAmount(5900, "EUR"):
            raise ValueError("introductory offer amount must be 59 EUR")
        if self.valid_until.tzinfo is None or self.valid_until.utcoffset() is None:
            raise ValueError("introductory offer deadline must be timezone-aware")
        if self.version <= 0:
            raise ValueError("introductory offer version must be positive")

    def is_available_at(self, now: datetime) -> bool:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("offer evaluation time must be timezone-aware")
        return now < self.valid_until
