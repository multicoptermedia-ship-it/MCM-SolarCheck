from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from mcm_solarcheck.infrastructure.sqlite_voucher import (
    SQLiteFlightPlanVoucherPolicyStore,
    SQLiteFlightPlanVoucherStore,
)
from mcm_solarcheck.services.voucher_admin import (
    FlightPlanVoucherAdminService,
    FlightPlanVoucherPolicy,
)


def test_admin_policy_defaults_to_ten_percent() -> None:
    assert FlightPlanVoucherPolicy().discount_percent == 10
    with pytest.raises(ValueError, match="must be 10 percent"):
        FlightPlanVoucherPolicy(12)


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


def test_voucher_policy_history_is_versioned_and_current_is_latest(tmp_path) -> None:
    store = SQLiteFlightPlanVoucherPolicyStore(tmp_path / "voucher.sqlite")
    first = FlightPlanVoucherPolicy()
    second = first.supersede()

    store.save(first)
    store.save(second)

    assert store.get(1).discount_percent == 10
    assert store.current() == second


def test_inactive_latest_voucher_policy_blocks_new_pricing_configuration(tmp_path) -> None:
    store = SQLiteFlightPlanVoucherPolicyStore(tmp_path / "voucher.sqlite")
    first = FlightPlanVoucherPolicy()
    store.save(first)
    store.save(first.deactivate())

    assert store.get(1).active
    assert not store.get(2).active
    with pytest.raises(ValueError, match="inactive"):
        store.current()


def test_voucher_policy_requires_strict_sequential_versions(tmp_path) -> None:
    store = SQLiteFlightPlanVoucherPolicyStore(tmp_path / "voucher.sqlite")
    store.save(FlightPlanVoucherPolicy())

    with pytest.raises(ValueError, match="version is not next"):
        store.save(FlightPlanVoucherPolicy(10, version=3))


def test_legacy_database_bootstraps_default_policy_once(tmp_path) -> None:
    database = tmp_path / "voucher.sqlite"
    vouchers = SQLiteFlightPlanVoucherStore(database)
    start = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    vouchers.create(
        __import__(
            "mcm_solarcheck.services.voucher",
            fromlist=["FlightPlanVoucher"],
        ).FlightPlanVoucher(
            "LEGACY-CODE",
            start,
            start + timedelta(days=30),
        )
    )

    policies = SQLiteFlightPlanVoucherPolicyStore(database)
    first = policies.bootstrap_default()
    second = policies.bootstrap_default()

    assert first == FlightPlanVoucherPolicy(10, version=1)
    assert second == first
    assert policies.current() == first
    assert vouchers.get("LEGACY-CODE").code == "LEGACY-CODE"


def test_bootstrap_never_overwrites_existing_policy_history(tmp_path) -> None:
    policies = SQLiteFlightPlanVoucherPolicyStore(tmp_path / "voucher.sqlite")
    policies.save(FlightPlanVoucherPolicy())
    inactive = FlightPlanVoucherPolicy().deactivate()
    policies.save(inactive)

    assert policies.bootstrap_default() == inactive
    assert policies.get(1).active
    assert not policies.get(2).active
