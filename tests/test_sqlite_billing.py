from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.sqlite_billing import SQLiteComputeJobBillingStore
from mcm_solarcheck.services.billing import ComputeJobBilling, ComputeJobDelivery


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
