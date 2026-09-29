from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier

from mcm_solarcheck.infrastructure.sqlite_voucher import SQLiteFlightPlanVoucherStore
from mcm_solarcheck.services.voucher import FlightPlanVoucher


def test_sqlite_voucher_persists_discount_snapshot_and_redemption(tmp_path) -> None:
    database = tmp_path / "voucher.sqlite"
    store = SQLiteFlightPlanVoucherStore(database)
    start = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    store.create(FlightPlanVoucher("FLIGHTPLAN-ABC123", start, start + timedelta(days=30)))

    redeemed = store.redeem(
        "FLIGHTPLAN-ABC123", "payment-a",
        discount_percent=10, now=start + timedelta(days=1)
    )

    restarted = SQLiteFlightPlanVoucherStore(database)
    assert restarted.get("FLIGHTPLAN-ABC123") == redeemed
    assert redeemed.redeemed_discount_percent == 10


def test_concurrent_voucher_redemption_has_exactly_one_winner(tmp_path) -> None:
    database = tmp_path / "voucher.sqlite"
    store = SQLiteFlightPlanVoucherStore(database)
    start = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    store.create(FlightPlanVoucher("FLIGHTPLAN-ABC123", start, start + timedelta(days=30)))
    barrier = Barrier(2)

    def redeem(payment_id: str) -> str:
        local = SQLiteFlightPlanVoucherStore(database)
        barrier.wait()
        try:
            local.redeem(
                "FLIGHTPLAN-ABC123", payment_id,
                discount_percent=10, now=start + timedelta(days=1)
            )
            return payment_id
        except ValueError as exc:
            assert "already redeemed" in str(exc)
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(redeem, ["payment-a", "payment-b"]))

    assert results.count("rejected") == 1
    persisted = store.get("FLIGHTPLAN-ABC123")
    assert persisted.redeemed_payment_id in {"payment-a", "payment-b"}
    assert persisted.redeemed_discount_percent == 10
