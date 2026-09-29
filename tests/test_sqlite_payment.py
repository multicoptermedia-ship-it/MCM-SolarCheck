from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from mcm_solarcheck.infrastructure.sqlite_payment import SQLiteOnlinePaymentStore
from mcm_solarcheck.services.payment import (
    OnlinePayment,
    PaymentAmount,
    PaymentStatus,
)
from mcm_solarcheck.services.payment_methods import PaymentMethod


def payment() -> OnlinePayment:
    return OnlinePayment(
        "payment-a",
        "user-a",
        "project-a",
        "job-a",
        PaymentAmount(12900, "EUR"),
    )


def test_sqlite_payment_lifecycle_persists_across_restart(tmp_path) -> None:
    database = tmp_path / "payment.sqlite"
    store = SQLiteOnlinePaymentStore(database)
    store.create(payment())

    authorized = store.authorize(
        "payment-a", "user-a", "project-a", "provider-auth-a"
    )
    assert authorized.status is PaymentStatus.AUTHORIZED

    restarted = SQLiteOnlinePaymentStore(database)
    assert restarted.get("payment-a") == authorized

    captured = restarted.capture("payment-a", "user-a", "project-a")
    assert captured.status is PaymentStatus.CAPTURED
    assert SQLiteOnlinePaymentStore(database).get("payment-a") == captured


def test_concurrent_capture_allows_exactly_one_transition(tmp_path) -> None:
    database = tmp_path / "payment.sqlite"
    store = SQLiteOnlinePaymentStore(database)
    store.create(payment())
    store.authorize("payment-a", "user-a", "project-a", "provider-auth-a")
    barrier = Barrier(2)

    def capture_once() -> str:
        local = SQLiteOnlinePaymentStore(database)
        barrier.wait()
        try:
            local.capture("payment-a", "user-a", "project-a")
            return "captured"
        except ValueError as exc:
            assert "authorized" in str(exc)
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: capture_once(), range(2)))

    assert sorted(results) == ["captured", "rejected"]
    assert store.get("payment-a").status is PaymentStatus.CAPTURED


def test_concurrent_capture_and_void_have_one_terminal_winner(tmp_path) -> None:
    database = tmp_path / "payment.sqlite"
    store = SQLiteOnlinePaymentStore(database)
    store.create(payment())
    store.authorize("payment-a", "user-a", "project-a", "provider-auth-a")
    barrier = Barrier(2)

    def transition(action: str) -> str:
        local = SQLiteOnlinePaymentStore(database)
        barrier.wait()
        try:
            if action == "capture":
                local.capture("payment-a", "user-a", "project-a")
            else:
                local.void("payment-a", "user-a", "project-a")
            return action
        except ValueError as exc:
            assert "authorized" in str(exc)
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(transition, ["capture", "void"]))

    assert results.count("rejected") == 1
    assert store.get("payment-a").status in {
        PaymentStatus.CAPTURED,
        PaymentStatus.VOIDED,
    }


def test_selected_payment_method_persists_across_lifecycle(tmp_path) -> None:
    database = tmp_path / "payment-method.sqlite"
    store = SQLiteOnlinePaymentStore(database)
    selected = OnlinePayment(
        "payment-method",
        "user-a",
        "project-a",
        "job-a",
        PaymentAmount(12900, "EUR"),
        method=PaymentMethod.CARD,
    )
    store.create(selected)

    authorized = store.authorize(
        "payment-method", "user-a", "project-a", "provider-auth-method"
    )
    assert authorized.method is PaymentMethod.CARD

    captured = store.capture(
        "payment-method", "user-a", "project-a"
    )
    assert captured.method is PaymentMethod.CARD
    assert SQLiteOnlinePaymentStore(database).get(
        "payment-method"
    ).method is PaymentMethod.CARD


def test_merchant_account_snapshot_survives_account_change(tmp_path) -> None:
    database = tmp_path / "payment-account.sqlite"
    store = SQLiteOnlinePaymentStore(database)
    first = OnlinePayment(
        "payment-account-a",
        "user-a",
        "project-a",
        "job-a",
        PaymentAmount(12900, "EUR"),
        method=PaymentMethod.PAYPAL,
        merchant_account_id="paypal-main",
        merchant_account_version=1,
    )
    store.create(first)

    second = OnlinePayment(
        "payment-account-b",
        "user-a",
        "project-b",
        "job-b",
        PaymentAmount(15900, "EUR"),
        method=PaymentMethod.PAYPAL,
        merchant_account_id="paypal-main",
        merchant_account_version=2,
    )
    store.create(second)

    assert store.get("payment-account-a").merchant_account_version == 1
    assert store.get("payment-account-b").merchant_account_version == 2
