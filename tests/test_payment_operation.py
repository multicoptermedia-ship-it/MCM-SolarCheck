from __future__ import annotations

import pytest

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
