from __future__ import annotations

import pytest

from mcm_solarcheck.services.billing import ComputeJobDelivery


@pytest.mark.parametrize(
    ("export_completed", "report_retrieved", "billable"),
    [
        (False, False, False),
        (True, False, False),
        (False, True, False),
        (True, True, True),
    ],
)
def test_compute_job_billing_requires_export_and_report_retrieval(
    export_completed: bool,
    report_retrieved: bool,
    billable: bool,
) -> None:
    delivery = ComputeJobDelivery(
        "job-a",
        export_completed=export_completed,
        report_retrieved=report_retrieved,
    )

    assert delivery.billable is billable


def test_compute_job_delivery_requires_job_identity() -> None:
    with pytest.raises(ValueError):
        ComputeJobDelivery(" ")
