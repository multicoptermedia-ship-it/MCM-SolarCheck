from __future__ import annotations

from typing import get_type_hints

from mcm_solarcheck.services.compute_job_store import ComputeJobStore
from mcm_solarcheck.services.compute_jobs import ComputeJob


def test_compute_job_store_exposes_durable_state_operations() -> None:
    assert callable(getattr(ComputeJobStore, "create", None))
    assert callable(getattr(ComputeJobStore, "get", None))
    assert callable(getattr(ComputeJobStore, "update", None))


def test_compute_job_store_contract_uses_compute_job_identity() -> None:
    create_hints = get_type_hints(ComputeJobStore.create)
    get_hints = get_type_hints(ComputeJobStore.get)
    update_hints = get_type_hints(ComputeJobStore.update)

    assert create_hints["job"] is ComputeJob
    assert get_hints["job_id"] is str
    assert get_hints["return"] is ComputeJob
    assert update_hints["job"] is ComputeJob
