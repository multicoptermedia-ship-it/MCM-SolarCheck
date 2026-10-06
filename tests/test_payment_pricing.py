from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import sqlite3

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


def test_atomic_priced_payment_store_rejects_wal_payment_database(tmp_path) -> None:
    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    vouchers = SQLiteFlightPlanVoucherStore(tmp_path / "vouchers.sqlite")
    connection = sqlite3.connect(payments.database)
    try:
        assert connection.execute("PRAGMA journal_mode=WAL").fetchone()[0].lower() == "wal"
    finally:
        connection.close()

    with pytest.raises(ValueError, match="does not support WAL"):
        SQLitePricedPaymentStore(payments.database, vouchers.database)


def test_atomic_priced_payment_store_rejects_wal_voucher_database(tmp_path) -> None:
    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    vouchers = SQLiteFlightPlanVoucherStore(tmp_path / "vouchers.sqlite")
    connection = sqlite3.connect(vouchers.database)
    try:
        assert connection.execute("PRAGMA journal_mode=WAL").fetchone()[0].lower() == "wal"
    finally:
        connection.close()

    with pytest.raises(ValueError, match="does not support WAL"):
        SQLitePricedPaymentStore(payments.database, vouchers.database)


def test_voucher_redemption_snapshots_persisted_policy_version(tmp_path) -> None:
    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    vouchers = SQLiteFlightPlanVoucherStore(tmp_path / "vouchers.sqlite")
    policies = SQLiteFlightPlanVoucherPolicyStore(tmp_path / "vouchers.sqlite")
    now = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)
    vouchers.create(
        FlightPlanVoucher(
            "FLIGHTPLAN-POLICY-V2",
            now - timedelta(days=1),
            now + timedelta(days=30),
        )
    )
    policies.save(FlightPlanVoucherPolicy())
    policies.save(FlightPlanVoucherPolicy().supersede())

    service = PaymentPricingService(
        payments,
        vouchers,
        policies,
        SQLitePricedPaymentStore(payments.database, vouchers.database),
    )
    service.create_payment(
        "payment-policy-v2",
        user_id="user-a",
        project_id="project-a",
        job_id="job-policy-v2",
        base_amount=PaymentAmount(50000, "EUR"),
        voucher_code="FLIGHTPLAN-POLICY-V2",
        now=now,
    )

    redeemed = vouchers.get("FLIGHTPLAN-POLICY-V2")
    assert redeemed.redeemed_discount_percent == 10
    assert redeemed.redeemed_policy_version == 2
    assert policies.get(redeemed.redeemed_policy_version).discount_percent == 10


def test_legacy_voucher_schema_migrates_without_inventing_policy_version(tmp_path) -> None:
    database = tmp_path / "legacy-vouchers.sqlite"
    now = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)
    connection = sqlite3.connect(database)
    connection.execute(
        """
        CREATE TABLE flightplan_vouchers (
            code TEXT PRIMARY KEY,
            valid_from TEXT NOT NULL,
            valid_until TEXT NOT NULL,
            redeemed_payment_id TEXT,
            redeemed_at TEXT,
            redeemed_discount_percent INTEGER
        )
        """
    )
    connection.execute(
        """
        INSERT INTO flightplan_vouchers (
            code, valid_from, valid_until, redeemed_payment_id,
            redeemed_at, redeemed_discount_percent
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "FLIGHTPLAN-LEGACY",
            (now - timedelta(days=1)).isoformat(),
            (now + timedelta(days=30)).isoformat(),
            "payment-legacy",
            now.isoformat(),
            10,
        ),
    )
    connection.commit()
    connection.close()

    vouchers = SQLiteFlightPlanVoucherStore(database)
    legacy = vouchers.get("FLIGHTPLAN-LEGACY")

    assert legacy.redeemed_payment_id == "payment-legacy"
    assert legacy.redeemed_discount_percent == 10
    assert legacy.redeemed_policy_version is None


def test_atomic_priced_payment_store_supports_shared_database(tmp_path) -> None:
    database = tmp_path / "shared.sqlite"
    payments = SQLiteOnlinePaymentStore(database)
    vouchers = SQLiteFlightPlanVoucherStore(database)
    now = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)
    vouchers.create(FlightPlanVoucher("SHARED-DB", now - timedelta(days=1), now + timedelta(days=1)))
    service = PaymentPricingService(
        payments,
        vouchers,
        FlightPlanVoucherPolicy(10),
        SQLitePricedPaymentStore(database, database),
    )

    payment = service.create_payment(
        "payment-shared-db",
        user_id="user-a",
        project_id="project-a",
        job_id="job-shared-db",
        base_amount=PaymentAmount(5900, "EUR"),
        voucher_code="SHARED-DB",
        now=now,
    )

    assert payment.amount == PaymentAmount(5310, "EUR")
    assert payments.get("payment-shared-db") == payment
    assert vouchers.get("SHARED-DB").redeemed_payment_id == "payment-shared-db"


def test_shared_database_missing_voucher_does_not_create_payment(tmp_path) -> None:
    database = tmp_path / "shared.sqlite"
    payments = SQLiteOnlinePaymentStore(database)
    vouchers = SQLiteFlightPlanVoucherStore(database)
    service = PaymentPricingService(
        payments,
        vouchers,
        FlightPlanVoucherPolicy(10),
        SQLitePricedPaymentStore(database, database),
    )

    with pytest.raises(KeyError):
        service.create_payment(
            "payment-missing-voucher",
            user_id="user-a",
            project_id="project-a",
            job_id="job-missing-voucher",
            base_amount=PaymentAmount(5900, "EUR"),
            voucher_code="MISSING",
            now=datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc),
        )

    with pytest.raises(KeyError):
        payments.get("payment-missing-voucher")


def test_shared_database_duplicate_job_does_not_redeem_voucher(tmp_path) -> None:
    database = tmp_path / "shared.sqlite"
    payments = SQLiteOnlinePaymentStore(database)
    vouchers = SQLiteFlightPlanVoucherStore(database)
    now = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)
    vouchers.create(FlightPlanVoucher("SHARED-DUPJOB", now - timedelta(days=1), now + timedelta(days=1)))
    service = PaymentPricingService(
        payments,
        vouchers,
        FlightPlanVoucherPolicy(10),
        SQLitePricedPaymentStore(database, database),
    )
    service.create_payment(
        "payment-existing-shared",
        user_id="user-a",
        project_id="project-a",
        job_id="job-shared-duplicate",
        base_amount=PaymentAmount(5900, "EUR"),
        now=now,
    )

    with pytest.raises(ValueError, match="already has a payment"):
        service.create_payment(
            "payment-duplicate-shared",
            user_id="user-a",
            project_id="project-a",
            job_id="job-shared-duplicate",
            base_amount=PaymentAmount(5900, "EUR"),
            voucher_code="SHARED-DUPJOB",
            now=now,
        )

    assert vouchers.get("SHARED-DUPJOB").redeemed is False


def test_shared_database_redeemed_voucher_rejects_second_payment(tmp_path) -> None:
    database = tmp_path / "shared.sqlite"
    payments = SQLiteOnlinePaymentStore(database)
    vouchers = SQLiteFlightPlanVoucherStore(database)
    now = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)
    vouchers.create(FlightPlanVoucher("SHARED-ONCE", now - timedelta(days=1), now + timedelta(days=1)))
    service = PaymentPricingService(
        payments,
        vouchers,
        FlightPlanVoucherPolicy(10),
        SQLitePricedPaymentStore(database, database),
    )
    service.create_payment(
        "payment-shared-first",
        user_id="user-a",
        project_id="project-a",
        job_id="job-shared-first",
        base_amount=PaymentAmount(5900, "EUR"),
        voucher_code="SHARED-ONCE",
        now=now,
    )

    with pytest.raises(ValueError, match="already redeemed"):
        service.create_payment(
            "payment-shared-second",
            user_id="user-a",
            project_id="project-b",
            job_id="job-shared-second",
            base_amount=PaymentAmount(5900, "EUR"),
            voucher_code="SHARED-ONCE",
            now=now,
        )

    with pytest.raises(KeyError):
        payments.get("payment-shared-second")


def test_shared_database_voucher_redemption_persists_policy_evidence(tmp_path) -> None:
    database = tmp_path / "shared.sqlite"
    payments = SQLiteOnlinePaymentStore(database)
    vouchers = SQLiteFlightPlanVoucherStore(database)
    policies = SQLiteFlightPlanVoucherPolicyStore(database)
    policies.save(FlightPlanVoucherPolicy())
    policies.save(FlightPlanVoucherPolicy().supersede())
    now = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)
    vouchers.create(FlightPlanVoucher("SHARED-POLICY", now - timedelta(days=1), now + timedelta(days=1)))
    service = PaymentPricingService(
        payments,
        vouchers,
        policies,
        SQLitePricedPaymentStore(database, database),
    )

    service.create_payment(
        "payment-shared-policy",
        user_id="user-a",
        project_id="project-a",
        job_id="job-shared-policy",
        base_amount=PaymentAmount(5900, "EUR"),
        voucher_code="SHARED-POLICY",
        now=now,
    )

    redeemed = vouchers.get("SHARED-POLICY")
    assert redeemed.redeemed_discount_percent == 10
    assert redeemed.redeemed_policy_version == 2
    assert redeemed.redeemed_at == now


def test_pricing_rejects_second_payment_for_same_job_without_voucher(tmp_path) -> None:
    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    vouchers = SQLiteFlightPlanVoucherStore(tmp_path / "vouchers.sqlite")
    service = PaymentPricingService(payments, vouchers, FlightPlanVoucherPolicy(10))
    now = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)
    service.create_payment(
        "payment-job-first", user_id="user-a", project_id="project-a",
        job_id="job-one-payment", base_amount=PaymentAmount(5900, "EUR"), now=now,
    )

    with pytest.raises(ValueError, match="already has a payment"):
        service.create_payment(
            "payment-job-second", user_id="user-a", project_id="project-a",
            job_id="job-one-payment", base_amount=PaymentAmount(5900, "EUR"), now=now,
        )

    with pytest.raises(KeyError):
        payments.get("payment-job-second")


def test_duplicate_job_rejection_preserves_original_payment(tmp_path) -> None:
    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    vouchers = SQLiteFlightPlanVoucherStore(tmp_path / "vouchers.sqlite")
    service = PaymentPricingService(payments, vouchers, FlightPlanVoucherPolicy(10))
    now = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)
    first = service.create_payment(
        "payment-original-job", user_id="user-a", project_id="project-a",
        job_id="job-preserved", base_amount=PaymentAmount(5900, "EUR"), now=now,
    )

    with pytest.raises(ValueError, match="already has a payment"):
        service.create_payment(
            "payment-rejected-job", user_id="user-b", project_id="project-b",
            job_id="job-preserved", base_amount=PaymentAmount(14500, "EUR"), now=now,
        )

    assert payments.get("payment-original-job") == first


def test_settled_payment_also_blocks_second_job_payment(tmp_path) -> None:
    from mcm_solarcheck.services.payment import OnlinePayment

    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    settled = OnlinePayment(
        "payment-settled-job", "user-a", "project-a", "job-settled",
        None, PaymentStatus.SETTLED,
    )
    payments.create(settled)

    with pytest.raises(ValueError, match="already has a payment"):
        payments.create(
            OnlinePayment(
                "payment-after-settled-job", "user-a", "project-a", "job-settled",
                PaymentAmount(5900, "EUR"),
            )
        )

    assert payments.get("payment-settled-job") == settled


def test_payment_store_duplicate_job_raises_domain_value_error(tmp_path) -> None:
    from mcm_solarcheck.services.payment import OnlinePayment

    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    first = OnlinePayment(
        "payment-store-first", "user-a", "project-a", "job-store-duplicate",
        PaymentAmount(5900, "EUR"),
    )
    second = OnlinePayment(
        "payment-store-second", "user-a", "project-a", "job-store-duplicate",
        PaymentAmount(5900, "EUR"),
    )
    payments.create(first)

    with pytest.raises(ValueError, match="compute job already has a payment"):
        payments.create(second)


def test_pricing_never_creates_zero_payable_user_job(tmp_path) -> None:
    class FullDiscountPolicy:
        active = True
        discount_percent = 100
        version = 99

    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    vouchers = SQLiteFlightPlanVoucherStore(tmp_path / "vouchers.sqlite")
    now = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)
    vouchers.create(FlightPlanVoucher("NO-FREE-JOB", now - timedelta(days=1), now + timedelta(days=1)))
    service = PaymentPricingService(
        payments, vouchers, FullDiscountPolicy(),
        SQLitePricedPaymentStore(payments.database, vouchers.database),
    )

    with pytest.raises(ValueError, match="positive payable amount"):
        service.create_payment(
            "payment-no-free-job", user_id="user-a", project_id="project-a",
            job_id="job-no-free", base_amount=PaymentAmount(5900, "EUR"),
            voucher_code="NO-FREE-JOB", now=now,
        )


def test_rejected_zero_payable_job_is_not_persisted(tmp_path) -> None:
    class FullDiscountPolicy:
        active = True
        discount_percent = 100
        version = 99

    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    vouchers = SQLiteFlightPlanVoucherStore(tmp_path / "vouchers.sqlite")
    now = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)
    vouchers.create(FlightPlanVoucher("NO-FREE-PERSIST", now - timedelta(days=1), now + timedelta(days=1)))
    service = PaymentPricingService(
        payments, vouchers, FullDiscountPolicy(),
        SQLitePricedPaymentStore(payments.database, vouchers.database),
    )

    with pytest.raises(ValueError, match="positive payable amount"):
        service.create_payment(
            "payment-no-free-persist", user_id="user-a", project_id="project-a",
            job_id="job-no-free-persist", base_amount=PaymentAmount(5900, "EUR"),
            voucher_code="NO-FREE-PERSIST", now=now,
        )

    with pytest.raises(KeyError):
        payments.get("payment-no-free-persist")


def test_rejected_zero_payable_job_does_not_redeem_voucher(tmp_path) -> None:
    class FullDiscountPolicy:
        active = True
        discount_percent = 100
        version = 99

    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    vouchers = SQLiteFlightPlanVoucherStore(tmp_path / "vouchers.sqlite")
    now = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)
    vouchers.create(FlightPlanVoucher("NO-FREE-REDEEM", now - timedelta(days=1), now + timedelta(days=1)))
    service = PaymentPricingService(
        payments, vouchers, FullDiscountPolicy(),
        SQLitePricedPaymentStore(payments.database, vouchers.database),
    )

    with pytest.raises(ValueError, match="positive payable amount"):
        service.create_payment(
            "payment-no-free-redeem", user_id="user-a", project_id="project-a",
            job_id="job-no-free-redeem", base_amount=PaymentAmount(5900, "EUR"),
            voucher_code="NO-FREE-REDEEM", now=now,
        )

    assert vouchers.get("NO-FREE-REDEEM").redeemed is False


def test_valid_flightplan_voucher_always_leaves_positive_charge(tmp_path) -> None:
    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    vouchers = SQLiteFlightPlanVoucherStore(tmp_path / "vouchers.sqlite")
    now = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)
    vouchers.create(FlightPlanVoucher("PAID-JOB", now - timedelta(days=1), now + timedelta(days=1)))
    service = PaymentPricingService(
        payments, vouchers, FlightPlanVoucherPolicy(),
        SQLitePricedPaymentStore(payments.database, vouchers.database),
    )

    payment = service.create_payment(
        "payment-paid-job", user_id="user-a", project_id="project-a",
        job_id="job-paid", base_amount=PaymentAmount(5900, "EUR"),
        voucher_code="PAID-JOB", now=now,
    )

    assert payment.amount == PaymentAmount(5310, "EUR")
    assert payment.status is PaymentStatus.CREATED


def test_concurrent_duplicate_job_creation_has_one_winner(tmp_path) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from mcm_solarcheck.services.payment import OnlinePayment

    database = tmp_path / "payments.sqlite"
    store = SQLiteOnlinePaymentStore(database)
    first = OnlinePayment("payment-race-a", "user-a", "project-a", "job-race", PaymentAmount(5900, "EUR"))
    second = OnlinePayment("payment-race-b", "user-a", "project-a", "job-race", PaymentAmount(5900, "EUR"))

    def create(payment):
        try:
            SQLiteOnlinePaymentStore(database).create(payment)
            return "created"
        except ValueError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, (first, second)))

    assert sorted(results) == ["created", "rejected"]


def test_concurrent_duplicate_job_preserves_winning_payment(tmp_path) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from mcm_solarcheck.services.payment import OnlinePayment

    database = tmp_path / "payments.sqlite"
    store = SQLiteOnlinePaymentStore(database)
    payments = (
        OnlinePayment("payment-winner-a", "user-a", "project-a", "job-winner", PaymentAmount(5900, "EUR")),
        OnlinePayment("payment-winner-b", "user-b", "project-b", "job-winner", PaymentAmount(6900, "EUR")),
    )

    def create(payment):
        try:
            SQLiteOnlinePaymentStore(database).create(payment)
            return payment
        except ValueError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(create, payments))

    winner = next(payment for payment in outcomes if payment is not None)
    assert store.get(winner.payment_id) == winner


def test_concurrent_duplicate_job_rejection_is_domain_value_error(tmp_path) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from mcm_solarcheck.services.payment import OnlinePayment

    database = tmp_path / "payments.sqlite"
    SQLiteOnlinePaymentStore(database)
    payments = (
        OnlinePayment("payment-domain-a", "user-a", "project-a", "job-domain-race", PaymentAmount(5900, "EUR")),
        OnlinePayment("payment-domain-b", "user-a", "project-a", "job-domain-race", PaymentAmount(5900, "EUR")),
    )

    def create(payment):
        try:
            SQLiteOnlinePaymentStore(database).create(payment)
            return None
        except Exception as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        errors = [error for error in pool.map(create, payments) if error is not None]

    assert len(errors) == 1
    assert type(errors[0]) is ValueError
    assert str(errors[0]) == "compute job already has a payment"


def test_concurrent_duplicate_job_leaves_exactly_one_job_row(tmp_path) -> None:
    from concurrent.futures import ThreadPoolExecutor
    import sqlite3
    from mcm_solarcheck.services.payment import OnlinePayment

    database = tmp_path / "payments.sqlite"
    SQLiteOnlinePaymentStore(database)
    payments = (
        OnlinePayment("payment-row-a", "user-a", "project-a", "job-one-row", PaymentAmount(5900, "EUR")),
        OnlinePayment("payment-row-b", "user-a", "project-a", "job-one-row", PaymentAmount(5900, "EUR")),
    )

    def create(payment):
        try:
            SQLiteOnlinePaymentStore(database).create(payment)
        except ValueError:
            pass

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(create, payments))

    with sqlite3.connect(database) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM online_payments WHERE job_id = ?",
            ("job-one-row",),
        ).fetchone()[0]
    assert count == 1


def test_payment_store_duplicate_payment_id_raises_domain_value_error(tmp_path) -> None:
    from mcm_solarcheck.services.payment import OnlinePayment

    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    payments.create(OnlinePayment("payment-same-id", "user-a", "project-a", "job-a", PaymentAmount(5900, "EUR")))

    with pytest.raises(ValueError, match="payment id already exists"):
        payments.create(OnlinePayment("payment-same-id", "user-a", "project-a", "job-b", PaymentAmount(6900, "EUR")))


def test_duplicate_payment_id_rejection_preserves_original_payment(tmp_path) -> None:
    from mcm_solarcheck.services.payment import OnlinePayment

    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    original = OnlinePayment("payment-preserved-id", "user-a", "project-a", "job-original-id", PaymentAmount(5900, "EUR"))
    payments.create(original)

    with pytest.raises(ValueError, match="payment id already exists"):
        payments.create(OnlinePayment("payment-preserved-id", "user-b", "project-b", "job-other-id", PaymentAmount(6900, "EUR")))

    assert payments.get("payment-preserved-id") == original


def test_duplicate_payment_id_rejection_does_not_reserve_second_job(tmp_path) -> None:
    from mcm_solarcheck.services.payment import OnlinePayment

    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    payments.create(OnlinePayment("payment-reusable-job-id", "user-a", "project-a", "job-first-id", PaymentAmount(5900, "EUR")))

    with pytest.raises(ValueError, match="payment id already exists"):
        payments.create(OnlinePayment("payment-reusable-job-id", "user-a", "project-a", "job-second-id", PaymentAmount(5900, "EUR")))

    second = OnlinePayment("payment-new-id", "user-a", "project-a", "job-second-id", PaymentAmount(5900, "EUR"))
    payments.create(second)
    assert payments.get("payment-new-id") == second
