from __future__ import annotations

import pytest
import sqlite3

from mcm_solarcheck.infrastructure.sqlite_payment_operation import (
    SQLitePaymentOperationIntentStore,
)
from mcm_solarcheck.services.payment_operation import (
    PaymentOperation,
    PaymentOperationIntent,
    PaymentOperationStatus,
)


def test_same_terminal_payment_intent_is_idempotent(tmp_path) -> None:
    store = SQLitePaymentOperationIntentStore(tmp_path / "operations.sqlite")
    intent = PaymentOperationIntent("payment-a", PaymentOperation.CAPTURE, "payment:payment-a:capture")

    assert store.reserve(intent) == intent
    assert store.reserve(intent) == intent


@pytest.mark.parametrize(
    ("first", "second"),
    [
        (PaymentOperation.CAPTURE, PaymentOperation.VOID),
        (PaymentOperation.VOID, PaymentOperation.CAPTURE),
    ],
)
def test_conflicting_terminal_payment_intent_is_rejected(
    tmp_path,
    first,
    second,
) -> None:
    store = SQLitePaymentOperationIntentStore(tmp_path / "operations.sqlite")
    store.reserve(PaymentOperationIntent("payment-a", first, f"payment:payment-a:{first.value}"))

    with pytest.raises(ValueError, match="conflicting terminal"):
        store.reserve(PaymentOperationIntent("payment-a", second, f"payment:payment-a:{second.value}"))


def test_payment_operation_lifecycle_is_persistent_and_idempotent(tmp_path) -> None:
    store = SQLitePaymentOperationIntentStore(tmp_path / "operations.sqlite")
    intent = PaymentOperationIntent(
        "payment-a",
        PaymentOperation.CAPTURE,
        "payment:payment-a:capture",
    )
    store.reserve(intent)

    succeeded = store.mark_provider_succeeded("payment-a")
    assert succeeded.status is PaymentOperationStatus.PROVIDER_SUCCEEDED
    assert store.mark_provider_succeeded("payment-a") == succeeded

    completed = store.mark_completed("payment-a")
    assert completed.status is PaymentOperationStatus.COMPLETED
    assert store.mark_completed("payment-a") == completed
    assert store.get("payment-a") == completed


def test_payment_operation_rejects_changed_idempotency_key(tmp_path) -> None:
    store = SQLitePaymentOperationIntentStore(tmp_path / "operations.sqlite")
    store.reserve(
        PaymentOperationIntent(
            "payment-a",
            PaymentOperation.CAPTURE,
            "payment:payment-a:capture",
        )
    )

    with pytest.raises(ValueError, match="idempotency key"):
        store.reserve(
            PaymentOperationIntent(
                "payment-a",
                PaymentOperation.CAPTURE,
                "changed-key",
            )
        )


@pytest.mark.parametrize(
    "status",
    [PaymentOperationStatus.PROVIDER_SUCCEEDED, PaymentOperationStatus.COMPLETED],
)
def test_new_payment_operation_cannot_skip_reserved_state(tmp_path, status) -> None:
    store = SQLitePaymentOperationIntentStore(tmp_path / "operations.sqlite")

    with pytest.raises(ValueError, match="must be reserved"):
        store.reserve(
            PaymentOperationIntent(
                "payment-a",
                PaymentOperation.CAPTURE,
                "payment:payment-a:capture",
                status,
            )
        )

    with pytest.raises(KeyError):
        store.get("payment-a")


def test_payment_operation_storage_stays_minimal(tmp_path) -> None:
    database = tmp_path / "operations.sqlite"
    SQLitePaymentOperationIntentStore(database)

    with sqlite3.connect(database) as connection:
        columns = [
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(payment_operation_intents)"
            )
        ]

    assert columns == ["payment_id", "operation", "idempotency_key", "status"]


def test_legacy_payment_operation_migrates_and_restart_is_idempotent(tmp_path) -> None:
    database = tmp_path / "legacy-operations.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE payment_operation_intents (
                payment_id TEXT PRIMARY KEY,
                operation TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO payment_operation_intents (payment_id, operation)
            VALUES (?, ?)
            """,
            ("payment-a", PaymentOperation.CAPTURE.value),
        )

    first = SQLitePaymentOperationIntentStore(database)
    migrated = first.get("payment-a")
    assert migrated.idempotency_key == "payment:payment-a:capture"
    assert migrated.status is PaymentOperationStatus.RESERVED

    second = SQLitePaymentOperationIntentStore(database)
    assert second.get("payment-a") == migrated

    succeeded = second.mark_provider_succeeded("payment-a")
    restarted = SQLitePaymentOperationIntentStore(database)
    assert restarted.get("payment-a") == succeeded
    completed = restarted.mark_completed("payment-a")
    assert completed.status is PaymentOperationStatus.COMPLETED
