from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from mcm_solarcheck.services.payment import PaymentAmount
from mcm_solarcheck.services.voucher import FlightPlanVoucher, discounted_amount


def voucher(*, value: int = 2500) -> FlightPlanVoucher:
    start = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    return FlightPlanVoucher(
        "FLIGHTPLAN-ABC123",
        PaymentAmount(value, "EUR"),
        start,
        start + timedelta(days=30),
    )


def test_voucher_value_is_separate_from_code() -> None:
    item = voucher(value=3500)
    assert item.code == "FLIGHTPLAN-ABC123"
    assert item.value == PaymentAmount(3500, "EUR")


def test_voucher_is_valid_only_inside_explicit_window() -> None:
    item = voucher()
    with pytest.raises(ValueError, match="not valid"):
        item.redeem("payment-a", now=item.valid_from - timedelta(seconds=1))

    redeemed = item.redeem("payment-a", now=item.valid_from)
    assert redeemed.redeemed_payment_id == "payment-a"

    with pytest.raises(ValueError, match="not valid"):
        item.redeem("payment-b", now=item.valid_until)


def test_voucher_is_one_time_only() -> None:
    item = voucher()
    redeemed = item.redeem("payment-a", now=item.valid_from)

    with pytest.raises(ValueError, match="already redeemed"):
        redeemed.redeem("payment-b", now=item.valid_from + timedelta(seconds=1))


def test_voucher_discount_never_creates_negative_payment() -> None:
    item = voucher(value=3500)

    assert discounted_amount(PaymentAmount(12900, "EUR"), item) == PaymentAmount(
        9400, "EUR"
    )
    assert discounted_amount(PaymentAmount(3500, "EUR"), item) is None
    assert discounted_amount(PaymentAmount(2000, "EUR"), item) is None


def test_voucher_currency_must_match_payment() -> None:
    with pytest.raises(ValueError, match="currency"):
        discounted_amount(PaymentAmount(12900, "USD"), voucher())
