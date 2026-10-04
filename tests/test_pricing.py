from decimal import Decimal

import pytest

from mcm_solarcheck.domain.pricing import PriceTier, PricingRule


def rule() -> PricingRule:
    return PricingRule(
        version="2026-10-test",
        tiers=(
            PriceTier(Decimal("30"), Decimal("300")),
            PriceTier(Decimal("100"), Decimal("500")),
            PriceTier(None, Decimal("900")),
        ),
        planner_discount_rate=Decimal("0.10"),
        repeat_discount_rate=Decimal("0.05"),
        maximum_discount_rate=Decimal("0.12"),
    )


@pytest.mark.parametrize(
    ("capacity", "expected"),
    [
        ("30", "300.00"),
        ("30.01", "500.00"),
        ("100", "500.00"),
        ("100.01", "900.00"),
    ],
)
def test_pricing_tier_boundaries_are_deterministic(capacity: str, expected: str) -> None:
    assert rule().price(Decimal(capacity)).net_total == Decimal(expected)


def test_verified_discounts_are_explicit_and_capped() -> None:
    snapshot = rule().price(
        Decimal("50"),
        planner_verified=True,
        repeat_verified=True,
    )

    assert snapshot.discount_rate == Decimal("0.12")
    assert snapshot.discount_amount == Decimal("60.00")
    assert snapshot.net_total == Decimal("440.00")


def test_unverified_discount_claims_do_not_change_price() -> None:
    snapshot = rule().price(Decimal("50"))

    assert snapshot.discount_rate == Decimal("0")
    assert snapshot.net_total == Decimal("500.00")


def test_snapshot_preserves_rule_version() -> None:
    snapshot = rule().price(Decimal("10"))

    assert snapshot.rule_version == "2026-10-test"
    assert snapshot.capacity_kwp == Decimal("10")


@pytest.mark.parametrize("capacity", ["0", "-1"])
def test_non_positive_capacity_is_rejected(capacity: str) -> None:
    with pytest.raises(ValueError):
        rule().price(Decimal(capacity))
