from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from mcm_solarcheck.services.payment import PaymentAmount
from mcm_solarcheck.services.voucher import FlightPlanVoucher, discounted_amount


def voucher() -> FlightPlanVoucher:
    start = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    return FlightPlanVoucher(
        "FLIGHTPLAN-ABC123",
        start,
        start + timedelta(days=30),
    )


def test_voucher_code_has_no_embedded_monetary_value() -> None:
    item = voucher()
    assert item.code == "FLIGHTPLAN-ABC123"
    assert not hasattr(item, "value")


def test_voucher_is_valid_only_inside_explicit_window() -> None:
    item = voucher()
    with pytest.raises(ValueError, match="not valid"):
        item.redeem(
            "payment-a", discount_percent=10,
            now=item.valid_from - timedelta(seconds=1)
        )

    redeemed = item.redeem(
        "payment-a", discount_percent=10, now=item.valid_from
    )
    assert redeemed.redeemed_payment_id == "payment-a"
    assert redeemed.redeemed_discount_percent == 10

    with pytest.raises(ValueError, match="not valid"):
        item.redeem(
            "payment-b", discount_percent=10, now=item.valid_until
        )


def test_voucher_is_one_time_only_and_snapshots_discount() -> None:
    item = voucher()
    redeemed = item.redeem(
        "payment-a", discount_percent=10, now=item.valid_from
    )

    with pytest.raises(ValueError, match="already redeemed"):
        redeemed.redeem(
            "payment-b",
            discount_percent=12,
            now=item.valid_from + timedelta(seconds=1),
        )
    assert redeemed.redeemed_discount_percent == 10


def test_percentage_discount_scales_with_order_value() -> None:
    assert discounted_amount(
        PaymentAmount(10000, "EUR"), discount_percent=10
    ) == PaymentAmount(9000, "EUR")
    assert discounted_amount(
        PaymentAmount(50000, "EUR"), discount_percent=10
    ) == PaymentAmount(45000, "EUR")


def test_percentage_discount_uses_integer_minor_units() -> None:
    assert discounted_amount(
        PaymentAmount(9999, "EUR"), discount_percent=10
    ) == PaymentAmount(9000, "EUR")
    assert discounted_amount(
        PaymentAmount(12900, "EUR"), discount_percent=100
    ) is None

    with pytest.raises(ValueError, match="1 to 100"):
        discounted_amount(PaymentAmount(12900, "EUR"), discount_percent=0)
