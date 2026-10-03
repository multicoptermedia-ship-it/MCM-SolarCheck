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
