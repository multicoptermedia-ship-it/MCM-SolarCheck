"""Deterministic, versioned pricing rules for commercial offers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


MONEY = Decimal("0.01")


@dataclass(frozen=True)
class PriceTier:
    up_to_kwp: Decimal | None
    net_price: Decimal


@dataclass(frozen=True)
class PricingRule:
    version: str
    tiers: tuple[PriceTier, ...]
    planner_discount_rate: Decimal = Decimal("0")
    repeat_discount_rate: Decimal = Decimal("0")
    maximum_discount_rate: Decimal = Decimal("0")
    vat_rate: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if not self.version.strip() or not self.tiers:
            raise ValueError("pricing rule must be versioned and contain tiers")
        rates = (
            self.planner_discount_rate,
            self.repeat_discount_rate,
            self.maximum_discount_rate,
            self.vat_rate,
        )
        if any(not rate.is_finite() for rate in rates):
            raise ValueError("pricing rates must be finite")
        if any(rate < 0 for rate in rates):
            raise ValueError("pricing rates must not be negative")
        if any(rate > 1 for rate in rates):
            raise ValueError("pricing rates must not exceed 1")
        if (
            (self.planner_discount_rate > 0 or self.repeat_discount_rate > 0)
            and self.maximum_discount_rate == 0
        ):
            raise ValueError("configured discounts require a positive maximum discount rate")

        previous_limit = Decimal("0")
        for index, tier in enumerate(self.tiers):
            if not tier.net_price.is_finite() or (tier.up_to_kwp is not None and not tier.up_to_kwp.is_finite()):
                raise ValueError("tier values must be finite")
            if tier.net_price < 0:
                raise ValueError("tier prices must not be negative")
            if tier.up_to_kwp is None:
                if index != len(self.tiers) - 1:
                    raise ValueError("open-ended tier must be last")
                continue
            if tier.up_to_kwp <= previous_limit:
                raise ValueError("tier limits must be positive and strictly increasing")
            previous_limit = tier.up_to_kwp

    def price(self, capacity_kwp: Decimal, *, planner_verified: bool = False, repeat_verified: bool = False) -> "PriceSnapshot":
        if not capacity_kwp.is_finite():
            raise ValueError("capacity_kwp must be finite")
        if capacity_kwp <= 0:
            raise ValueError("capacity_kwp must be positive")
        if not self.version.strip() or not self.tiers:
            raise ValueError("pricing rule must be versioned and contain tiers")
        tier = next((item for item in self.tiers if item.up_to_kwp is None or capacity_kwp <= item.up_to_kwp), None)
        if tier is None:
            raise ValueError("pricing rule does not cover capacity")
        requested_discount = (
            (self.planner_discount_rate if planner_verified else Decimal("0"))
            + (self.repeat_discount_rate if repeat_verified else Decimal("0"))
        )
        discount_rate = min(requested_discount, self.maximum_discount_rate)
        net_before_discount = tier.net_price.quantize(MONEY, rounding=ROUND_HALF_UP)
        discount_amount = (net_before_discount * discount_rate).quantize(MONEY, rounding=ROUND_HALF_UP)
        net_total = (net_before_discount - discount_amount).quantize(MONEY, rounding=ROUND_HALF_UP)
        vat_amount = (net_total * self.vat_rate).quantize(MONEY, rounding=ROUND_HALF_UP)
        return PriceSnapshot(
            rule_version=self.version,
            capacity_kwp=capacity_kwp,
            net_before_discount=net_before_discount,
            discount_rate=discount_rate,
            discount_amount=discount_amount,
            net_total=net_total,
            vat_rate=self.vat_rate,
            vat_amount=vat_amount,
            gross_total=(net_total + vat_amount).quantize(MONEY, rounding=ROUND_HALF_UP),
            rule_tiers=self.tiers,
            planner_discount_rate=self.planner_discount_rate,
            repeat_discount_rate=self.repeat_discount_rate,
            maximum_discount_rate=self.maximum_discount_rate,
        )


@dataclass(frozen=True)
class PriceSnapshot:
    rule_version: str
    capacity_kwp: Decimal
    net_before_discount: Decimal
    discount_rate: Decimal
    discount_amount: Decimal
    net_total: Decimal
    vat_rate: Decimal
    vat_amount: Decimal
    gross_total: Decimal
    rule_tiers: tuple[PriceTier, ...]
    planner_discount_rate: Decimal
    repeat_discount_rate: Decimal
    maximum_discount_rate: Decimal
