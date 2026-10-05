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
        vat_rate=Decimal("0.19"),
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


def test_tax_is_separate_from_discounted_net_total() -> None:
    snapshot = rule().price(Decimal("50"), planner_verified=True)

    assert snapshot.net_total == Decimal("450.00")
    assert snapshot.vat_rate == Decimal("0.19")
    assert snapshot.vat_amount == Decimal("85.50")
    assert snapshot.gross_total == Decimal("535.50")


def test_snapshot_contains_complete_pricing_rule() -> None:
    pricing = rule()
    snapshot = pricing.price(Decimal("10"))

    assert snapshot.rule_tiers == pricing.tiers
    assert snapshot.planner_discount_rate == Decimal("0.10")
    assert snapshot.repeat_discount_rate == Decimal("0.05")
    assert snapshot.maximum_discount_rate == Decimal("0.12")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"version": ""},
        {"tiers": ()},
        {"planner_discount_rate": Decimal("-0.01")},
        {"repeat_discount_rate": Decimal("-0.01")},
        {"planner_discount_rate": Decimal("1.01")},
        {"repeat_discount_rate": Decimal("1.01")},
        {"maximum_discount_rate": Decimal("1.01")},
        {"vat_rate": Decimal("1.01")},
    ],
)
def test_invalid_pricing_rule_configuration_is_rejected(kwargs) -> None:
    values = {
        "version": "2026-10-test",
        "tiers": (PriceTier(None, Decimal("300")),),
        "planner_discount_rate": Decimal("0"),
        "repeat_discount_rate": Decimal("0"),
        "maximum_discount_rate": Decimal("0"),
        "vat_rate": Decimal("0.19"),
    }
    values.update(kwargs)

    with pytest.raises(ValueError):
        PricingRule(**values)


def test_tier_limits_must_be_strictly_increasing() -> None:
    with pytest.raises(ValueError):
        PricingRule(
            version="2026-10-test",
            tiers=(
                PriceTier(Decimal("100"), Decimal("500")),
                PriceTier(Decimal("30"), Decimal("300")),
            ),
        )


def test_open_ended_tier_must_be_last() -> None:
    with pytest.raises(ValueError):
        PricingRule(
            version="2026-10-test",
            tiers=(
                PriceTier(None, Decimal("300")),
                PriceTier(Decimal("100"), Decimal("500")),
            ),
        )


def test_negative_tier_price_is_rejected() -> None:
    with pytest.raises(ValueError):
        PricingRule(
            version="2026-10-test",
            tiers=(PriceTier(None, Decimal("-0.01")),),
        )


def test_configured_discount_requires_positive_cap() -> None:
    with pytest.raises(ValueError, match="positive maximum discount"):
        PricingRule(
            version="2026-10-test",
            tiers=(PriceTier(None, Decimal("300")),),
            planner_discount_rate=Decimal("0.10"),
        )


def test_zero_discount_cap_is_valid_without_configured_discounts() -> None:
    pricing = PricingRule(
        version="2026-10-test",
        tiers=(PriceTier(None, Decimal("300")),),
    )

    assert pricing.price(Decimal("10")).net_total == Decimal("300.00")


def test_planner_discount_is_ten_percent_when_verified() -> None:
    snapshot = rule().price(Decimal("50"), planner_verified=True)

    assert snapshot.planner_discount_rate == Decimal("0.10")
    assert snapshot.discount_rate == Decimal("0.10")
    assert snapshot.discount_amount == Decimal("50.00")
