"""Versioned, admin-manageable pricing for SolarCheck evaluation services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from mcm_solarcheck.services.payment import PaymentAmount


@dataclass(frozen=True)
class SolarCheckPriceBand:
    min_kwp: int
    max_kwp: int
    amount: PaymentAmount

    def __post_init__(self) -> None:
        if not isinstance(self.min_kwp, int) or isinstance(self.min_kwp, bool):
            raise ValueError("min_kwp must be an integer")
        if not isinstance(self.max_kwp, int) or isinstance(self.max_kwp, bool):
            raise ValueError("max_kwp must be an integer")
        if self.min_kwp < 0:
            raise ValueError("min_kwp must not be negative")
        if self.max_kwp < self.min_kwp:
            raise ValueError("max_kwp must be greater than or equal to min_kwp")


@dataclass(frozen=True)
class SolarCheckTariff:
    version: int
    bands: tuple[SolarCheckPriceBand, ...]
    effective_from: datetime
    active: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.version, int) or isinstance(self.version, bool):
            raise ValueError("tariff version must be an integer")
        if self.version <= 0:
            raise ValueError("tariff version must be positive")
        if self.effective_from.tzinfo is None or self.effective_from.utcoffset() is None:
            raise ValueError("tariff effective_from must be timezone-aware")
        if not self.bands:
            raise ValueError("tariff requires at least one price band")
        currency = self.bands[0].amount.currency
        previous = None
        for band in self.bands:
            if band.amount.currency != currency:
                raise ValueError("all tariff bands must use the same currency")
            if previous is not None and band.min_kwp != previous.max_kwp + 1:
                raise ValueError("tariff bands must be contiguous and non-overlapping")
            previous = band

    def price_for(self, plant_kwp: int) -> PaymentAmount:
        if not isinstance(plant_kwp, int) or isinstance(plant_kwp, bool):
            raise ValueError("plant_kwp must be an integer")
        if plant_kwp < 0:
            raise ValueError("plant_kwp must not be negative")
        for band in self.bands:
            if band.min_kwp <= plant_kwp <= band.max_kwp:
                return band.amount
        raise ValueError("plant size is outside the configured tariff")


@dataclass(frozen=True)
class SolarCheckPriceQuote:
    plant_kwp: int
    amount: PaymentAmount
    tariff_version: int
    quoted_at: datetime


def quote_solarcheck(
    tariff: SolarCheckTariff,
    *,
    plant_kwp: int,
    quoted_at: datetime,
) -> SolarCheckPriceQuote:
    if quoted_at.tzinfo is None or quoted_at.utcoffset() is None:
        raise ValueError("quoted_at must be timezone-aware")
    if quoted_at < tariff.effective_from:
        raise ValueError("tariff is not effective yet")
    if not tariff.active:
        raise ValueError("inactive tariff cannot create new quotes")
    return SolarCheckPriceQuote(
        plant_kwp,
        tariff.price_for(plant_kwp),
        tariff.version,
        quoted_at,
    )


def initial_solarcheck_tariff(effective_from: datetime) -> SolarCheckTariff:
    """Initial tariff supplied by the product owner; future edits create new versions."""

    euro = "EUR"
    rows = (
        (0, 50, 9500),
        (51, 100, 10500),
        (101, 150, 11500),
        (151, 200, 12500),
        (201, 499, 13500),
        (500, 999, 14500),
        (1000, 1499, 15500),
        (1500, 1999, 16500),
        (2000, 2499, 17500),
        (2500, 2999, 18500),
        (3000, 3999, 19500),
        (4000, 4999, 20500),
        (5000, 5999, 21500),
        (6000, 7999, 22500),
        (8000, 10000, 23500),
    )
    return SolarCheckTariff(
        1,
        tuple(
            SolarCheckPriceBand(start, end, PaymentAmount(cents, euro))
            for start, end, cents in rows
        ),
        effective_from,
    )



class SolarCheckTariffPersistence(Protocol):
    """Provider-neutral persistence for versioned SolarCheck tariffs."""

    def save(self, tariff: SolarCheckTariff) -> None:
        ...

    def current(self, at: datetime) -> SolarCheckTariff:
        """Return the active tariff effective at the supplied instant."""
        ...

    def is_configured(self) -> bool:
        """Return whether production has an effective active tariff."""
        ...
