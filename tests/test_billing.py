from __future__ import annotations

import pytest

from mcm_solarcheck.services.billing import ComputeJobBilling, ComputeJobDelivery


@pytest.mark.parametrize(
    ("export_completed", "report_retrieved", "billable"),
    [
        (False, False, False),
        (True, False, False),
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
        "user-a",
        "project-a",
        export_completed=export_completed,
        report_retrieved=report_retrieved,
    )

    assert delivery.billable is billable


def test_compute_job_delivery_requires_job_identity() -> None:
    with pytest.raises(ValueError):
        ComputeJobDelivery(" ", "user-a", "project-a")



def test_compute_job_billing_release_requires_delivered_result() -> None:
    billing = ComputeJobBilling(
        ComputeJobDelivery(
            "job-a",
            "user-a",
            "project-a",
            export_completed=True,
            report_retrieved=False,
        )
    )

    with pytest.raises(ValueError, match="not billable"):
        billing.release()


def test_compute_job_billing_release_is_one_time() -> None:
    billing = ComputeJobBilling(
        ComputeJobDelivery(
            "job-a",
            "user-a",
            "project-a",
            export_completed=True,
            report_retrieved=True,
        )
    )

    released = billing.release()

    assert released.billing_released is True
    with pytest.raises(ValueError, match="already released"):
        released.release()


def test_released_billing_cannot_be_constructed_without_complete_delivery() -> None:
    with pytest.raises(ValueError, match="export and report retrieval"):
        ComputeJobBilling(
            ComputeJobDelivery(
                "job-a",
                "user-a",
                "project-a",
                export_completed=True,
                report_retrieved=False,
            ),
            billing_released=True,
        )

    with pytest.raises(ValueError, match="export and report retrieval"):
        ComputeJobBilling(
            ComputeJobDelivery(
                "job-a",
                "user-a",
                "project-a",
                export_completed=False,
                report_retrieved=True,
            ),
            billing_released=True,
        )


def test_report_retrieval_without_export_is_invalid_delivery_state() -> None:
    with pytest.raises(ValueError, match="requires completed export"):
        ComputeJobDelivery(
            "job-a",
            "user-a",
            "project-a",
            export_completed=False,
            report_retrieved=True,
        )
