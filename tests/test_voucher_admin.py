from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from mcm_solarcheck.infrastructure.sqlite_voucher import SQLiteFlightPlanVoucherStore
from mcm_solarcheck.services.voucher_admin import (
    FlightPlanVoucherAdminService,
    FlightPlanVoucherPolicy,
)


def test_admin_policy_defaults_to_ten_percent() -> None:
    assert FlightPlanVoucherPolicy().discount_percent == 10
    assert FlightPlanVoucherPolicy(12).discount_percent == 12


def test_admin_creates_voucher_validity_without_individual_value(tmp_path) -> None:
    store = SQLiteFlightPlanVoucherStore(tmp_path / "voucher.sqlite")
    admin = FlightPlanVoucherAdminService(store)
    start = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)

    created = admin.create(
        "FLIGHTPLAN-ABC123",
        valid_from=start,
        valid_until=start + timedelta(days=30),
    )

    assert not hasattr(created, "value")
    assert store.get("FLIGHTPLAN-ABC123") == created


def test_admin_cannot_create_duplicate_voucher_code(tmp_path) -> None:
    store = SQLiteFlightPlanVoucherStore(tmp_path / "voucher.sqlite")
    admin = FlightPlanVoucherAdminService(store)
    start = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    kwargs = dict(valid_from=start, valid_until=start + timedelta(days=30))

    admin.create("FLIGHTPLAN-ABC123", **kwargs)
    with pytest.raises(Exception):
        admin.create("FLIGHTPLAN-ABC123", **kwargs)
