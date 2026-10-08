from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from mcm_solarcheck.infrastructure.sqlite_solarcheck_tariff import (
    SQLiteSolarCheckTariffStore,
)
from mcm_solarcheck.services.payment import PaymentAmount
from mcm_solarcheck.services.solarcheck_tariff import (
    SolarCheckPriceBand,
    SolarCheckTariff,
    initial_solarcheck_tariff,
    quote_solarcheck,
)


def test_initial_tariff_matches_product_owner_price_table() -> None:
    now = datetime(2026, 9, 30, 10, 0, tzinfo=timezone.utc)
    tariff = initial_solarcheck_tariff(now)

    expected = (
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
    assert tuple(
        (band.min_kwp, band.max_kwp, band.amount.minor_units)
        for band in tariff.bands
    ) == expected


def test_quote_keeps_tariff_version_and_amount_snapshot() -> None:
    now = datetime(2026, 9, 30, 10, 0, tzinfo=timezone.utc)
    original = initial_solarcheck_tariff(now)
    quote = quote_solarcheck(original, plant_kwp=750, quoted_at=now)

    edited = SolarCheckTariff(
        2,
        tuple(
            SolarCheckPriceBand(
                band.min_kwp,
                band.max_kwp,
                PaymentAmount(
                    band.amount.minor_units + 1000
                    if band.min_kwp == 500
                    else band.amount.minor_units,
                    "EUR",
                ),
            )
            for band in original.bands
        ),
        now + timedelta(days=1),
    )

    assert quote.amount == PaymentAmount(14500, "EUR")
    assert quote.tariff_version == 1
    assert edited.price_for(750) == PaymentAmount(15500, "EUR")


def test_tariff_rejects_gaps_or_overlaps() -> None:
    now = datetime(2026, 9, 30, 10, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="contiguous"):
        SolarCheckTariff(
            1,
            (
                SolarCheckPriceBand(0, 50, PaymentAmount(9500, "EUR")),
                SolarCheckPriceBand(52, 100, PaymentAmount(10500, "EUR")),
            ),
            now,
        )


def test_store_selects_newest_effective_active_tariff_without_repricing_history(tmp_path) -> None:
    store = SQLiteSolarCheckTariffStore(tmp_path / "tariffs.sqlite")
    now = datetime(2026, 9, 30, 10, 0, tzinfo=timezone.utc)
    first = initial_solarcheck_tariff(now)
    second = SolarCheckTariff(
        2,
        tuple(
            SolarCheckPriceBand(
                band.min_kwp,
                band.max_kwp,
                PaymentAmount(band.amount.minor_units + 1000, "EUR"),
            )
            for band in first.bands
        ),
        now + timedelta(days=1),
    )
    store.save(first)
    store.save(second)

    assert store.current(now).version == 1
    assert store.current(now + timedelta(days=2)).version == 2
    assert store.current(now).price_for(50) == PaymentAmount(9500, "EUR")
    assert store.current(now + timedelta(days=2)).price_for(50) == PaymentAmount(10500, "EUR")


def test_inactive_tariff_cannot_quote_new_order() -> None:
    now = datetime(2026, 9, 30, 10, 0, tzinfo=timezone.utc)
    tariff = initial_solarcheck_tariff(now)
    inactive = SolarCheckTariff(tariff.version, tariff.bands, tariff.effective_from, False)

    with pytest.raises(ValueError, match="inactive"):
        quote_solarcheck(inactive, plant_kwp=50, quoted_at=now)
