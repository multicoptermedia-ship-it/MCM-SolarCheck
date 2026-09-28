from __future__ import annotations

import pytest

from mcm_solarcheck.services.compute_jobs import ComputeJob, ComputeJobStatus


def test_compute_job_preserves_tenant_and_project_identity() -> None:
    job = ComputeJob(
        job_id="job-a",
        user_id="user-a",
        project_id="project-a",
        status=ComputeJobStatus.QUEUED,
    )

    assert job.job_id == "job-a"
    assert job.user_id == "user-a"
    assert job.project_id == "project-a"
    assert job.status is ComputeJobStatus.QUEUED


@pytest.mark.parametrize("field", ("job_id", "user_id", "project_id"))
@pytest.mark.parametrize("value", ("", "   ", None))
def test_compute_job_rejects_missing_identity(field, value) -> None:
    values = {
        "job_id": "job-a",
        "user_id": "user-a",
        "project_id": "project-a",
        "status": ComputeJobStatus.QUEUED,
    }
    values[field] = value

    with pytest.raises(ValueError, match=field):
        ComputeJob(**values)


def test_compute_job_rejects_untyped_status_fail_closed() -> None:
    with pytest.raises(ValueError, match="ComputeJobStatus"):
        ComputeJob(
            job_id="job-a",
            user_id="user-a",
            project_id="project-a",
            status="queued",
        )


def test_distinct_users_can_hold_distinct_queued_jobs() -> None:
    first = ComputeJob(
        job_id="job-a",
        user_id="user-a",
        project_id="project-a",
        status=ComputeJobStatus.QUEUED,
    )
    second = ComputeJob(
        job_id="job-b",
        user_id="user-b",
        project_id="project-b",
        status=ComputeJobStatus.QUEUED,
    )

    assert first.job_id != second.job_id
    assert first.user_id != second.user_id
    assert first.project_id != second.project_id
