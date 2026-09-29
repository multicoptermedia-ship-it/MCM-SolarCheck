from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from mcm_solarcheck.infrastructure.sqlite_voucher import SQLiteFlightPlanVoucherStore
from mcm_solarcheck.services.payment import PaymentAmount
from mcm_solarcheck.services.voucher_admin import FlightPlanVoucherAdminService


def test_admin_defines_voucher_value_and_validity(tmp_path) -> None:
    store = SQLiteFlightPlanVoucherStore(tmp_path / "voucher.sqlite")
    admin = FlightPlanVoucherAdminService(store)
    start = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)

    created = admin.create(
        "FLIGHTPLAN-ABC123",
        value_minor_units=3500,
        currency="EUR",
        valid_from=start,
        valid_until=start + timedelta(days=30),
    )

    assert created.value == PaymentAmount(3500, "EUR")
    assert store.get("FLIGHTPLAN-ABC123") == created


def test_admin_cannot_create_duplicate_voucher_code(tmp_path) -> None:
    store = SQLiteFlightPlanVoucherStore(tmp_path / "voucher.sqlite")
    admin = FlightPlanVoucherAdminService(store)
    start = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    kwargs = dict(
        value_minor_units=3500,
        currency="EUR",
        valid_from=start,
        valid_until=start + timedelta(days=30),
    )

    admin.create("FLIGHTPLAN-ABC123", **kwargs)
    with pytest.raises(Exception):
        admin.create("FLIGHTPLAN-ABC123", **kwargs)
