"""Synthetic 1000-capture flight planning tests."""
from mcm_solarcheck.services.flight_batch_plan import plan_flight_batches


def test_thousand_pairs_all_covered_without_manual_selection(tmp_path):
    for i in range(1000):
        for modality in ("V", "T"):
            (tmp_path / f"DJI_20260725154421_{i:04d}_{modality}.JPG").write_bytes(b"test")
    result = plan_flight_batches(tmp_path)
    assert result["capture_count"] == 1000
    assert len(result["batches"]) > 1
    covered = set()
    for batch in result["batches"]:
        assert len(batch["captures"]) <= 80
        covered.update(key for key, _, _ in batch["captures"])
    assert len(covered) == 1000
    assert sum(len(b["captures"]) for b in result["batches"]) > 1000


def test_small_flight_one_batch_with_missing_thermal_preserved(tmp_path):
    for i in range(10):
        (tmp_path / f"DJI_20260725154421_{i:04d}_V.JPG").write_bytes(b"test")
    result = plan_flight_batches(tmp_path)
    assert len(result["batches"]) == 1
    assert len(result["batches"][0]["captures"]) == 10
    assert all(thermal is None for _, _, thermal in result["batches"][0]["captures"])
