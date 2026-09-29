from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.sqlite_payment_operation import (
    SQLitePaymentOperationIntentStore,
)
from mcm_solarcheck.services.payment_operation import (
    PaymentOperation,
    PaymentOperationIntent,
)


def test_same_terminal_payment_intent_is_idempotent(tmp_path) -> None:
    store = SQLitePaymentOperationIntentStore(tmp_path / "operations.sqlite")
    intent = PaymentOperationIntent("payment-a", PaymentOperation.CAPTURE)

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
    store.reserve(PaymentOperationIntent("payment-a", first))

    with pytest.raises(ValueError, match="conflicting terminal"):
        store.reserve(PaymentOperationIntent("payment-a", second))
