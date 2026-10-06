from __future__ import annotations

import pytest

from mcm_solarcheck.services.payment import (
    OnlinePayment,
    PaymentAmount,
    PaymentStatus,
)


def test_payment_amount_uses_integer_minor_units() -> None:
    amount = PaymentAmount(12900, "eur")
    assert amount.minor_units == 12900
    assert amount.currency == "EUR"

    with pytest.raises(ValueError, match="integer"):
        PaymentAmount(129.0, "EUR")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="positive"):
        PaymentAmount(0, "EUR")


def test_payment_authorize_capture_lifecycle() -> None:
    payment = OnlinePayment(
        "payment-a",
        "user-a",
        "project-a",
        "job-a",
        PaymentAmount(12900, "EUR"),
    )

    authorized = payment.authorize("provider-auth-a")
    captured = authorized.capture()

    assert payment.status is PaymentStatus.CREATED
    assert authorized.status is PaymentStatus.AUTHORIZED
    assert captured.status is PaymentStatus.CAPTURED
    assert captured.provider_reference == "provider-auth-a"

    with pytest.raises(ValueError, match="authorized"):
        payment.capture()
    with pytest.raises(ValueError, match="authorized"):
        captured.capture()


def test_authorized_payment_can_be_voided_but_not_captured_afterwards() -> None:
    payment = OnlinePayment(
        "payment-a",
        "user-a",
        "project-a",
        "job-a",
        PaymentAmount(12900, "EUR"),
    ).authorize("provider-auth-a")

    voided = payment.void()

    assert voided.status is PaymentStatus.VOIDED
    with pytest.raises(ValueError, match="authorized"):
        voided.capture()
    with pytest.raises(ValueError, match="authorized"):
        voided.void()


def test_payment_identity_is_preserved_through_transitions() -> None:
    payment = OnlinePayment(
        "payment-a",
        "user-a",
        "project-a",
        "job-a",
        PaymentAmount(12900, "EUR"),
    )
    captured = payment.authorize("provider-auth-a").capture()

    assert captured.payment_id == "payment-a"
    assert captured.user_id == "user-a"
    assert captured.project_id == "project-a"
    assert captured.job_id == "job-a"
    assert captured.amount == PaymentAmount(12900, "EUR")


def test_online_payment_rejects_missing_amount_even_when_settled() -> None:
    with pytest.raises(ValueError, match="payment amount must be positive"):
        OnlinePayment(
            "payment-no-amount", "user-a", "project-a", "job-a",
            None, PaymentStatus.SETTLED,
        )
