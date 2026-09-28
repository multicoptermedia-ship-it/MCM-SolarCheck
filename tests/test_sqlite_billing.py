from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.sqlite_billing import SQLiteComputeJobBillingStore
from mcm_solarcheck.services.billing import (
    ComputeJobBilling,
    ComputeJobBillingService,
    ComputeJobDelivery,
)


def test_sqlite_compute_billing_persists_delivery_and_release(tmp_path) -> None:
    database = tmp_path / "billing.sqlite"
    store = SQLiteComputeJobBillingStore(database)
    billing = ComputeJobBilling(
        ComputeJobDelivery(
            "job-a",
            export_completed=True,
            report_retrieved=True,
        )
    )
    store.create(billing)

    released = billing.release()
    store.replace(released)

    restarted = SQLiteComputeJobBillingStore(database)
    persisted = restarted.get("job-a")

    assert persisted == released
    assert persisted.delivery.billable is True
    with pytest.raises(ValueError, match="already released"):
        persisted.release()


def test_sqlite_compute_billing_create_is_unique_per_job(tmp_path) -> None:
    store = SQLiteComputeJobBillingStore(tmp_path / "billing.sqlite")
    billing = ComputeJobBilling(ComputeJobDelivery("job-a"))
    store.create(billing)

    with pytest.raises(Exception):
        store.create(billing)



def test_billing_service_requires_server_delivery_events_before_release(tmp_path) -> None:
    store = SQLiteComputeJobBillingStore(tmp_path / "billing.sqlite")
    service = ComputeJobBillingService(store)
    service.create("job-a")

    retrieved = service.mark_report_retrieved("job-a")
    assert retrieved.delivery.report_retrieved is True
    assert retrieved.delivery.billable is False
    with pytest.raises(ValueError, match="not billable"):
        service.release("job-a")

    exported = service.mark_export_completed("job-a")
    assert exported.delivery.billable is True

    released = service.release("job-a")
    assert released.billing_released is True


def test_billing_delivery_events_are_idempotent(tmp_path) -> None:
    store = SQLiteComputeJobBillingStore(tmp_path / "billing.sqlite")
    service = ComputeJobBillingService(store)
    service.create("job-a")

    first_export = service.mark_export_completed("job-a")
    second_export = service.mark_export_completed("job-a")
    assert second_export == first_export

    first_retrieval = service.mark_report_retrieved("job-a")
    second_retrieval = service.mark_report_retrieved("job-a")
    assert second_retrieval == first_retrieval
    assert second_retrieval.delivery.billable is True
