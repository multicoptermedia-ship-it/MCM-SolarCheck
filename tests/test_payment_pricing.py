from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
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

    with pytest.raises(ValueError, match="must be 10 percent"):
        FlightPlanVoucherPolicy(12)
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


def test_flightplan_policy_cannot_be_configured_as_full_discount() -> None:
    with pytest.raises(ValueError, match="must be 10 percent"):
        FlightPlanVoucherPolicy(100)

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


def test_flightplan_discount_applies_only_to_payment_using_voucher(tmp_path) -> None:
    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    vouchers = SQLiteFlightPlanVoucherStore(tmp_path / "vouchers.sqlite")
    policies = SQLiteFlightPlanVoucherPolicyStore(tmp_path / "vouchers.sqlite")
    now = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    vouchers.create(
        FlightPlanVoucher(
            "FLIGHTPLAN-ONE-TIME",
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

    discounted = service.create_payment(
        "payment-with-flightplan",
        user_id="user-a",
        project_id="project-a",
        job_id="job-a",
        base_amount=PaymentAmount(50000, "EUR"),
        voucher_code="FLIGHTPLAN-ONE-TIME",
        now=now,
    )
    regular = service.create_payment(
        "payment-next-solarcheck",
        user_id="user-a",
        project_id="project-b",
        job_id="job-b",
        base_amount=PaymentAmount(50000, "EUR"),
        now=now + timedelta(seconds=1),
    )

    assert discounted.amount == PaymentAmount(45000, "EUR")
    assert regular.amount == PaymentAmount(50000, "EUR")
    assert vouchers.get(
        "FLIGHTPLAN-ONE-TIME"
    ).redeemed_discount_percent == 10


def test_redeemed_flightplan_code_cannot_discount_another_solarcheck(tmp_path) -> None:
    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    vouchers = SQLiteFlightPlanVoucherStore(tmp_path / "vouchers.sqlite")
    policies = SQLiteFlightPlanVoucherPolicyStore(tmp_path / "vouchers.sqlite")
    now = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    vouchers.create(
        FlightPlanVoucher(
            "FLIGHTPLAN-ONE-TIME",
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
    service.create_payment(
        "payment-a",
        user_id="user-a",
        project_id="project-a",
        job_id="job-a",
        base_amount=PaymentAmount(50000, "EUR"),
        voucher_code="FLIGHTPLAN-ONE-TIME",
        now=now,
    )

    with pytest.raises(ValueError, match="already redeemed"):
        service.create_payment(
            "payment-b",
            user_id="user-a",
            project_id="project-b",
            job_id="job-b",
            base_amount=PaymentAmount(50000, "EUR"),
            voucher_code="FLIGHTPLAN-ONE-TIME",
            now=now + timedelta(seconds=1),
        )


def test_same_flightplan_code_cannot_discount_two_concurrent_solarchecks(tmp_path) -> None:
    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    vouchers = SQLiteFlightPlanVoucherStore(tmp_path / "vouchers.sqlite")
    now = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    vouchers.create(
        FlightPlanVoucher(
            "FLIGHTPLAN-CONCURRENT",
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

    def create(payment_id, project_id, job_id):
        return service.create_payment(
            payment_id,
            user_id="user-a",
            project_id=project_id,
            job_id=job_id,
            base_amount=PaymentAmount(50000, "EUR"),
            voucher_code="FLIGHTPLAN-CONCURRENT",
            now=now,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(create, "payment-a", "project-a", "job-a"),
            executor.submit(create, "payment-b", "project-b", "job-b"),
        ]
        results = []
        errors = []
        for future in futures:
            try:
                results.append(future.result())
            except Exception as exc:
                errors.append(exc)

    assert len(results) == 1
    assert results[0].amount == PaymentAmount(45000, "EUR")
    assert len(errors) == 1
    assert "already redeemed" in str(errors[0])

    redeemed = vouchers.get("FLIGHTPLAN-CONCURRENT")
    assert redeemed.redeemed_discount_percent == 10
    assert redeemed.redeemed_payment_id == results[0].payment_id

    persisted = []
    for payment_id in ("payment-a", "payment-b"):
        try:
            persisted.append(payments.get(payment_id))
        except KeyError:
            pass
    assert persisted == results


def test_inactive_persisted_voucher_policy_does_not_block_full_price_payment(tmp_path) -> None:
    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    vouchers = SQLiteFlightPlanVoucherStore(tmp_path / "vouchers.sqlite")
    policies = SQLiteFlightPlanVoucherPolicyStore(tmp_path / "vouchers.sqlite")
    policies.save(FlightPlanVoucherPolicy())
    policies.save(FlightPlanVoucherPolicy().deactivate())
    service = PaymentPricingService(payments, vouchers, policies)

    payment = service.create_payment(
        "payment-full-price",
        user_id="user-a",
        project_id="project-a",
        job_id="job-a",
        base_amount=PaymentAmount(50000, "EUR"),
        now=datetime(2026, 9, 30, 9, 0, tzinfo=timezone.utc),
    )

    assert payment.amount == PaymentAmount(50000, "EUR")
    assert payments.get(payment.payment_id) == payment


def test_inactive_persisted_voucher_policy_blocks_voucher_payment(tmp_path) -> None:
    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    vouchers = SQLiteFlightPlanVoucherStore(tmp_path / "vouchers.sqlite")
    policies = SQLiteFlightPlanVoucherPolicyStore(tmp_path / "vouchers.sqlite")
    now = datetime(2026, 9, 30, 9, 0, tzinfo=timezone.utc)
    vouchers.create(
        FlightPlanVoucher(
            "FLIGHTPLAN-INACTIVE",
            now - timedelta(days=1),
            now + timedelta(days=30),
        )
    )
    policies.save(FlightPlanVoucherPolicy())
    policies.save(FlightPlanVoucherPolicy().deactivate())
    service = PaymentPricingService(
        payments,
        vouchers,
        policies,
        SQLitePricedPaymentStore(payments.database, vouchers.database),
    )

    with pytest.raises(ValueError, match="inactive"):
        service.create_payment(
            "payment-voucher",
            user_id="user-a",
            project_id="project-a",
            job_id="job-a",
            base_amount=PaymentAmount(50000, "EUR"),
            voucher_code="FLIGHTPLAN-INACTIVE",
            now=now,
        )

    assert vouchers.get("FLIGHTPLAN-INACTIVE").redeemed is False


def test_inactive_static_voucher_policy_only_blocks_voucher_payment(tmp_path) -> None:
    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    vouchers = SQLiteFlightPlanVoucherStore(tmp_path / "vouchers.sqlite")
    inactive = FlightPlanVoucherPolicy().deactivate()
    service = PaymentPricingService(payments, vouchers, inactive)
    now = datetime(2026, 9, 30, 9, 0, tzinfo=timezone.utc)

    regular = service.create_payment(
        "payment-regular",
        user_id="user-a",
        project_id="project-a",
        job_id="job-a",
        base_amount=PaymentAmount(50000, "EUR"),
        now=now,
    )
    assert regular.amount == PaymentAmount(50000, "EUR")

    vouchers.create(
        FlightPlanVoucher(
            "FLIGHTPLAN-STATIC-INACTIVE",
            now - timedelta(days=1),
            now + timedelta(days=30),
        )
    )
    atomic_service = PaymentPricingService(
        payments,
        vouchers,
        inactive,
        SQLitePricedPaymentStore(payments.database, vouchers.database),
    )
    with pytest.raises(ValueError, match="inactive"):
        atomic_service.create_payment(
            "payment-blocked",
            user_id="user-a",
            project_id="project-b",
            job_id="job-b",
            base_amount=PaymentAmount(50000, "EUR"),
            voucher_code="FLIGHTPLAN-STATIC-INACTIVE",
            now=now,
        )


def test_atomic_priced_payment_store_requires_initialized_payment_schema(tmp_path) -> None:
    vouchers = SQLiteFlightPlanVoucherStore(tmp_path / "vouchers.sqlite")

    with pytest.raises(ValueError, match="payment database schema is not initialized"):
        SQLitePricedPaymentStore(
            tmp_path / "uninitialized-payments.sqlite",
            vouchers.database,
        )


def test_atomic_priced_payment_store_requires_initialized_voucher_schema(tmp_path) -> None:
    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")

    with pytest.raises(ValueError, match="voucher database schema is not initialized"):
        SQLitePricedPaymentStore(
            payments.database,
            tmp_path / "uninitialized-vouchers.sqlite",
        )
