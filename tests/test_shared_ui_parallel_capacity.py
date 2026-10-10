"""Admission configuration is shared by create and retry endpoints."""
from pathlib import Path
from mcm_solarcheck.services.compute_jobs import ComputeCapacity

ROOT = Path(__file__).resolve().parents[1]


def test_capacity_validation():
    assert ComputeCapacity(2).can_start(0)
    assert ComputeCapacity(2).can_start(1)
    assert not ComputeCapacity(2).can_start(2)


def test_http_capacity_wired_to_both_routes():
    source = (ROOT / "src/mcm_solarcheck/infrastructure/verification_http_server.py").read_text(encoding="utf-8")
    entry = (ROOT / "src/mcm_solarcheck/online/http_entrypoint.py").read_text(encoding="utf-8")
    assert source.count("capacity=compute_capacity") == 2
    assert "compute_capacity = ComputeCapacity(max_parallel_compute_jobs)" in source
    assert "max_parallel_compute_jobs: int = 2" in entry
    assert "max_parallel_compute_jobs=max_parallel_compute_jobs" in entry
