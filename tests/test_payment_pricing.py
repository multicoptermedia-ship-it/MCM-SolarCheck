from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from mcm_solarcheck.infrastructure.sqlite_payment import SQLiteOnlinePaymentStore
from mcm_solarcheck.infrastructure.sqlite_priced_payment import SQLitePricedPaymentStore
from mcm_solarcheck.infrastructure.sqlite_voucher import (
    SQLiteFlightPlanVoucherPolicyStore,
    SQLiteFlightPlanVoucherStore,
)
from mcm_solarcheck.services.payment import PaymentAmount, PaymentStatus
from mcm_solarcheck.services.payment_pricing import PaymentPricingService
from mcm_solarcheck.services.voucher import FlightPlanVoucher
from mcm_solarcheck.services.voucher_admin import FlightPlanVoucherPolicy


def test_voucher_discount_is_fixed_in_payment_before_authorization(tmp_path) -> None:
    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    vouchers = SQLiteFlightPlanVoucherStore(tmp_path / "vouchers.sqlite")
    now = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    vouchers.create(
        FlightPlanVoucher(
            "FLIGHTPLAN-ABC123",
            now - timedelta(days=1),
            now + timedelta(days=30),
        )
    )
    service = PaymentPricingService(
        payments,
        vouchers,
        FlightPlanVoucherPolicy(10),
        SQLitePricedPaymentStore(payments.database, vouchers.database),
    )

    payment = service.create_payment(
        "payment-a",
        user_id="user-a",
        project_id="project-a",
        job_id="job-a",
        base_amount=PaymentAmount(50000, "EUR"),
        voucher_code="FLIGHTPLAN-ABC123",
        now=now,
    )

    assert payment is not None
    assert payment.amount == PaymentAmount(45000, "EUR")
    assert payments.get("payment-a").amount == PaymentAmount(45000, "EUR")
    assert (
        vouchers.get("FLIGHTPLAN-ABC123").redeemed_discount_percent == 10
    )


def test_later_policy_change_does_not_reprice_existing_payment(tmp_path) -> None:
    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    vouchers = SQLiteFlightPlanVoucherStore(tmp_path / "vouchers.sqlite")
    now = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    vouchers.create(
        FlightPlanVoucher(
            "FLIGHTPLAN-ABC123",
            now - timedelta(days=1),
            now + timedelta(days=30),
        )
    )
    PaymentPricingService(
        payments,
        vouchers,
        FlightPlanVoucherPolicy(10),
        SQLitePricedPaymentStore(payments.database, vouchers.database),
    ).create_payment(
        "payment-a",
        user_id="user-a",
        project_id="project-a",
        job_id="job-a",
        base_amount=PaymentAmount(50000, "EUR"),
        voucher_code="FLIGHTPLAN-ABC123",
        now=now,
    )

    assert FlightPlanVoucherPolicy(12).discount_percent == 12
    assert payments.get("payment-a").amount == PaymentAmount(45000, "EUR")


def test_payment_without_voucher_keeps_full_amount(tmp_path) -> None:
    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    vouchers = SQLiteFlightPlanVoucherStore(tmp_path / "vouchers.sqlite")
    service = PaymentPricingService(
        payments, vouchers, FlightPlanVoucherPolicy()
    )
    now = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)

    payment = service.create_payment(
        "payment-a",
        user_id="user-a",
        project_id="project-a",
        job_id="job-a",
        base_amount=PaymentAmount(50000, "EUR"),
        now=now,
    )

    assert payment is not None
    assert payment.amount == PaymentAmount(50000, "EUR")


def test_full_discount_persists_settled_payment_without_provider_amount(tmp_path) -> None:
    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    vouchers = SQLiteFlightPlanVoucherStore(tmp_path / "vouchers.sqlite")
    now = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    vouchers.create(
        FlightPlanVoucher(
            "FLIGHTPLAN-FULL",
            now - timedelta(days=1),
            now + timedelta(days=30),
        )
    )
    service = PaymentPricingService(
        payments,
        vouchers,
        FlightPlanVoucherPolicy(100),
        SQLitePricedPaymentStore(payments.database, vouchers.database),
    )

    payment = service.create_payment(
        "payment-free",
        user_id="user-a",
        project_id="project-a",
        job_id="job-a",
        base_amount=PaymentAmount(50000, "EUR"),
        voucher_code="FLIGHTPLAN-FULL",
        now=now,
    )

    assert payment.status is PaymentStatus.SETTLED
    assert payment.amount is None
    assert payment.provider_reference is None
    assert payments.get("payment-free") == payment
    assert (
        vouchers.get("FLIGHTPLAN-FULL").redeemed_payment_id == "payment-free"
    )


def test_failed_payment_insert_does_not_consume_voucher(tmp_path) -> None:
    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    vouchers = SQLiteFlightPlanVoucherStore(tmp_path / "vouchers.sqlite")
    now = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    vouchers.create(
        FlightPlanVoucher(
            "FLIGHTPLAN-ATOMIC",
            now - timedelta(days=1),
            now + timedelta(days=30),
        )
    )
    atomic = SQLitePricedPaymentStore(payments.database, vouchers.database)
    service = PaymentPricingService(
        payments,
        vouchers,
        FlightPlanVoucherPolicy(10),
        atomic,
    )
    service.create_payment(
        "payment-a",
        user_id="user-a",
        project_id="project-a",
        job_id="job-a",
        base_amount=PaymentAmount(50000, "EUR"),
        now=now,
    )

    with pytest.raises(Exception):
        service.create_payment(
            "payment-a",
            user_id="user-a",
            project_id="project-a",
            job_id="job-b",
            base_amount=PaymentAmount(50000, "EUR"),
            voucher_code="FLIGHTPLAN-ATOMIC",
            now=now,
        )

    voucher = vouchers.get("FLIGHTPLAN-ATOMIC")
    assert voucher.redeemed is False


def test_duplicate_job_payment_does_not_consume_voucher(tmp_path) -> None:
    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    vouchers = SQLiteFlightPlanVoucherStore(tmp_path / "vouchers.sqlite")
    now = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    vouchers.create(
        FlightPlanVoucher(
            "FLIGHTPLAN-DUPJOB",
            now - timedelta(days=1),
            now + timedelta(days=30),
        )
    )
    atomic = SQLitePricedPaymentStore(payments.database, vouchers.database)
    service = PaymentPricingService(
        payments,
        vouchers,
        FlightPlanVoucherPolicy(10),
        atomic,
    )
    service.create_payment(
        "payment-existing",
        user_id="user-a",
        project_id="project-a",
        job_id="job-a",
        base_amount=PaymentAmount(50000, "EUR"),
        now=now,
    )

    with pytest.raises(ValueError, match="already has a payment"):
        service.create_payment(
            "payment-duplicate",
            user_id="user-a",
            project_id="project-a",
            job_id="job-a",
            base_amount=PaymentAmount(50000, "EUR"),
            voucher_code="FLIGHTPLAN-DUPJOB",
            now=now,
        )

    assert vouchers.get("FLIGHTPLAN-DUPJOB").redeemed is False


def test_persisted_policy_change_only_affects_new_voucher_payments(tmp_path) -> None:
    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    vouchers = SQLiteFlightPlanVoucherStore(tmp_path / "vouchers.sqlite")
    policies = SQLiteFlightPlanVoucherPolicyStore(tmp_path / "vouchers.sqlite")
    now = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    for code in ("FLIGHTPLAN-OLD", "FLIGHTPLAN-NEW"):
        vouchers.create(
            FlightPlanVoucher(
                code,
                now - timedelta(days=1),
                now + timedelta(days=30),
            )
        )
    policies.save(FlightPlanVoucherPolicy(10))
    service = PaymentPricingService(
        payments,
        vouchers,
        policies,
        SQLitePricedPaymentStore(payments.database, vouchers.database),
    )

    old_payment = service.create_payment(
        "payment-old",
        user_id="user-a",
        project_id="project-a",
        job_id="job-old",
        base_amount=PaymentAmount(50000, "EUR"),
        voucher_code="FLIGHTPLAN-OLD",
        now=now,
    )
    policies.save(policies.current().supersede(discount_percent=20))
    new_payment = service.create_payment(
        "payment-new",
        user_id="user-a",
        project_id="project-a",
        job_id="job-new",
        base_amount=PaymentAmount(50000, "EUR"),
        voucher_code="FLIGHTPLAN-NEW",
        now=now + timedelta(seconds=1),
    )

    assert old_payment.amount == PaymentAmount(45000, "EUR")
    assert new_payment.amount == PaymentAmount(40000, "EUR")
    assert vouchers.get("FLIGHTPLAN-OLD").redeemed_discount_percent == 10
    assert vouchers.get("FLIGHTPLAN-NEW").redeemed_discount_percent == 20
