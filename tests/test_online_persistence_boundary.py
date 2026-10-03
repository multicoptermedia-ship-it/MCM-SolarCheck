from __future__ import annotations

from typing import get_type_hints

from mcm_solarcheck.infrastructure.online_persistence import OnlinePersistence


def test_online_persistence_container_has_no_sqlite_specific_type_contract() -> None:
    hints = get_type_hints(OnlinePersistence)

    sqlite_bound = [
        name
        for name, annotation in hints.items()
        if "SQLite" in getattr(annotation, "__name__", str(annotation))
    ]

    assert sqlite_bound == []


def test_registration_persistence_uses_service_layer_protocol() -> None:
    hints = get_type_hints(OnlinePersistence)

    assert hints["registrations"].__name__ == "OnlineRegistrationStore"
    assert hints["registrations"].__module__ == "mcm_solarcheck.services.online_registration"


def test_entitlement_persistence_uses_service_layer_protocol() -> None:
    hints = get_type_hints(OnlinePersistence)

    assert hints["entitlements"].__name__ == "OnlineEntitlementStore"
    assert hints["entitlements"].__module__ == "mcm_solarcheck.services.online_entitlement"


def test_compute_job_persistence_uses_atomic_composition_protocol() -> None:
    hints = get_type_hints(OnlinePersistence)

    assert hints["compute_jobs"].__name__ == "OnlineComputeJobPersistence"
    assert hints["compute_jobs"].__module__ == "mcm_solarcheck.services.compute_jobs"


def test_billing_persistence_uses_delivery_release_protocol() -> None:
    hints = get_type_hints(OnlinePersistence)

    assert hints["billing"].__name__ == "ComputeJobBillingStore"
    assert hints["billing"].__module__ == "mcm_solarcheck.services.billing"


def test_payment_persistence_includes_processing_snapshot_contract() -> None:
    hints = get_type_hints(OnlinePersistence)

    assert hints["payments"].__name__ == "OnlinePaymentPersistence"
    assert hints["payments"].__module__ == "mcm_solarcheck.services.payment"
    assert hasattr(hints["payments"], "bind_processing_snapshot")


def test_merchant_account_persistence_preserves_versioned_history_contract() -> None:
    hints = get_type_hints(OnlinePersistence)

    contract = hints["merchant_accounts"]
    assert contract.__name__ == "MerchantAccountPersistence"
    assert contract.__module__ == "mcm_solarcheck.services.merchant_account"
    for method in ("save", "get", "current", "is_configured"):
        assert hasattr(contract, method)


def test_tariff_persistence_preserves_versioned_pricing_contract() -> None:
    hints = get_type_hints(OnlinePersistence)

    contract = hints["tariffs"]
    assert contract.__name__ == "SolarCheckTariffPersistence"
    assert contract.__module__ == "mcm_solarcheck.services.solarcheck_tariff"
    for method in ("save", "current", "is_configured"):
        assert hasattr(contract, method)


def test_voucher_persistence_preserves_one_time_redemption_contract() -> None:
    hints = get_type_hints(OnlinePersistence)

    vouchers = hints["vouchers"]
    assert vouchers.__name__ == "FlightPlanVoucherPersistence"
    for method in ("create", "get", "redeem"):
        assert hasattr(vouchers, method)

    policy = hints["voucher_policy"]
    assert policy.__name__ == "FlightPlanVoucherPolicyPersistence"
    for method in ("bootstrap_default", "save", "get", "current"):
        assert hasattr(policy, method)

    atomic = hints["priced_payments"]
    assert atomic.__name__ == "AtomicPricedPaymentStore"
    assert hasattr(atomic, "create_with_voucher")


def test_payment_intent_persistence_uses_crash_safe_protocols() -> None:
    hints = get_type_hints(OnlinePersistence)

    operations = hints["payment_operations"]
    assert operations.__name__ == "PaymentOperationIntentStore"
    for method in ("reserve", "mark_provider_succeeded", "mark_completed", "get"):
        assert hasattr(operations, method)

    authorizations = hints["payment_authorizations"]
    assert authorizations.__name__ == "PaymentAuthorizationIntentStore"
    for method in ("reserve", "mark_provider_succeeded", "mark_completed", "get"):
        assert hasattr(authorizations, method)


def test_sepa_persistence_preserves_asynchronous_lifecycle_contracts() -> None:
    hints = get_type_hints(OnlinePersistence)

    mandates = hints["sepa_mandates"]
    assert mandates.__name__ == "SepaMandatePersistence"
    for method in ("create", "get", "activate", "revoke"):
        assert hasattr(mandates, method)

    submissions = hints["sepa_submissions"]
    assert submissions.__name__ == "SepaSubmissionPersistence"
    for method in ("reserve", "mark_submitted", "release", "get"):
        assert hasattr(submissions, method)

    collections = hints["sepa_collections"]
    assert collections.__name__ == "SepaCollectionPersistence"
    for method in (
        "create",
        "get",
        "get_by_provider_reference",
        "apply_provider_event",
        "transition",
    ):
        assert hasattr(collections, method)


def test_invoice_and_report_persistence_uses_service_layer_contracts() -> None:
    hints = get_type_hints(OnlinePersistence)

    identity = hints["invoice_identity"]
    assert identity.__name__ == "InvoiceIdentityStore"
    assert hasattr(identity, "reserve")

    delivery = hints["invoice_delivery"]
    assert delivery.__name__ == "InvoiceAdminDeliveryStateStore"
    for method in ("claim", "mark_sending", "mark_sent", "release"):
        assert hasattr(delivery, method)

    reports = hints["reports"]
    assert reports.__name__ == "ReportArtifactStore"
    assert hasattr(reports, "get")

    recovery = hints["report_recovery"]
    assert recovery.__name__ == "ReportRecoveryClaimStore"
    for method in ("claim", "mark_sent", "release"):
        assert hasattr(recovery, method)

    archive = hints["invoices"]
    assert archive.__name__ == "InvoiceArchive"
    for method in ("package_is_ready", "store", "store_package"):
        assert hasattr(archive, method)
