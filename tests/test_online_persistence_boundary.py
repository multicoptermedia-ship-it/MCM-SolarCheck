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
