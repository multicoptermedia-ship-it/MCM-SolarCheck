"""Local cohort comparison contracts: correctness, privacy and fail-closed."""
import json
from pathlib import Path

import pytest

from mcm_solarcheck.services.offline_benchmark_comparison import (
    MAX_REPORT_BYTES, compare_offline_benchmark_reports,
)
from mcm_solarcheck.services.offline_import_benchmark import (
    OfflineImportBenchmarkResult,
)
from mcm_solarcheck.services.offline_import_metrics import ImportPerformanceSnapshot


def _report(path, *, seconds=1.0, rss=2048, rgb=2, thermal=1,
            pairs=1, phase=0.5, outcome="succeeded"):
    measurement = ImportPerformanceSnapshot(
        elapsed_seconds=seconds, read_and_pair_seconds=phase,
        sqlite_commit_seconds=0.2 if phase is not None else None,
        observed_progress_updates=5, reported_checkpoints=2,
        process_peak_rss_bytes=rss,
        process_peak_rss_at_start_bytes=1024 if rss is not None else None,
        outcome=outcome,
    )
    payload = OfflineImportBenchmarkResult(
        measurement, rgb, thermal, pairs,
    ).anonymous_report()
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def _cohort(tmp_path):
    files = [tmp_path / f"local-{index}.json" for index in range(3)]
    for path, elapsed, rss in zip(files, (3.0, 2.0, 4.0),
                                   (3072, 2048, 4096)):
        _report(path, seconds=elapsed, rss=rss)
    return files


def test_comparison_has_median_range_counts_and_explicit_limits(tmp_path):
    paths = _cohort(tmp_path)
    comparison = compare_offline_benchmark_reports(paths)
    document = comparison.anonymous_report()
    assert document["run_count"] == 3
    assert document["elapsed_seconds"] == {
        "min": 2.0, "median": 3.0, "max": 4.0,
    }
    assert document["process_peak_rss_bytes"] == {
        "min": 2048, "median": 3072, "max": 4096,
    }
    assert document["persisted_rgb_frames_per_run"] == 2
    assert document["persisted_thermal_frames_per_run"] == 1
    assert document["all_runs_succeeded"] is True
    assert document["is_real_dji_validation"] is False
    assert document["is_windows_hardware_validated"] is False
    assert "not_isolated_import" in document["rss_scope"]
    assert "not_verified" in document["comparability"]
    assert not any(path.name in str(document) for path in paths)


def test_missing_rss_or_coarse_phases_stays_unknown_not_zero(tmp_path):
    paths = _cohort(tmp_path)
    _report(paths[1], seconds=2.0, rss=None, phase=None)
    report = compare_offline_benchmark_reports(paths).anonymous_report()
    assert report["process_peak_rss_bytes"] is None
    assert report["read_and_pair_seconds"] is None
    assert report["sqlite_commit_seconds"] is None
    assert report["elapsed_seconds"]["median"] == 3.0


@pytest.mark.parametrize("changed,error", [
    ({"outcome": "failed"}, "contract"),
    ({"schema_version": 1}, "contract"),
    ({"benchmark_kind": "other"}, "contract"),
    ({"contains_source_paths": True}, "contract"),
    ({"elapsed_seconds": -1}, "elapsed"),
    ({"elapsed_seconds": True}, "elapsed"),
    ({"read_and_pair_seconds": "1.0"}, "phase"),
    ({"progress_updates": 1.5}, "count"),
    ({"persisted_rgb_frames": -1}, "count"),
    ({"process_peak_rss_bytes": -7}, "RSS"),
    ({"process_peak_rss_bytes": 10}, "peak"),
])
def test_malformed_or_unsuccessful_reports_fail_closed(
    tmp_path, changed, error,
):
    paths = _cohort(tmp_path)
    altered = json.loads(paths[1].read_text(encoding="utf-8"))
    altered.update(changed)
    paths[1].write_text(json.dumps(altered), encoding="utf-8")
    with pytest.raises(ValueError, match=error):
        compare_offline_benchmark_reports(paths)


def test_unknown_private_field_is_rejected_not_echoed(tmp_path):
    paths = _cohort(tmp_path)
    altered = json.loads(paths[0].read_text(encoding="utf-8"))
    altered["private_customer_path"] = "CUSTOMER-DO-NOT-PRINT"
    paths[0].write_text(json.dumps(altered), encoding="utf-8")
    with pytest.raises(ValueError) as error:
        compare_offline_benchmark_reports(paths)
    assert "CUSTOMER-DO-NOT-PRINT" not in str(error.value)


def test_mixed_image_counts_do_not_claim_comparability(tmp_path):
    paths = _cohort(tmp_path)
    _report(paths[1], rgb=999)
    with pytest.raises(ValueError, match="frame counts differ"):
        compare_offline_benchmark_reports(paths)


def test_same_report_twice_is_rejected(tmp_path):
    paths = _cohort(tmp_path)
    with pytest.raises(ValueError, match="duplicate"):
        compare_offline_benchmark_reports([paths[0], paths[0], paths[1]])


def test_excessively_large_json_is_rejected_before_parsing(tmp_path):
    paths = _cohort(tmp_path)
    paths[0].write_bytes(b"{" + b"A" * MAX_REPORT_BYTES + b"}")
    with pytest.raises(ValueError, match="permitted size"):
        compare_offline_benchmark_reports(paths)


def test_nonfinite_numbers_and_zero_frame_counts_are_rejected(tmp_path):
    paths = _cohort(tmp_path)
    altered = json.loads(paths[0].read_text(encoding="utf-8"))
    altered["elapsed_seconds"] = float("nan")
    paths[0].write_text(json.dumps(altered), encoding="utf-8")
    with pytest.raises(ValueError, match="elapsed"):
        compare_offline_benchmark_reports(paths)
    _report(paths[0], rgb=0, thermal=0, pairs=0)
    with pytest.raises(ValueError, match="no persisted images"):
        compare_offline_benchmark_reports(paths)


def test_input_paths_must_be_absolute_and_not_symlinks(tmp_path):
    paths = _cohort(tmp_path)
    with pytest.raises(ValueError, match="absolute"):
        compare_offline_benchmark_reports(
            [Path("relative.json"), paths[1], paths[2]],
        )
    link = tmp_path / "alias.json"
    try:
        link.symlink_to(paths[0])
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links unsupported")
    with pytest.raises(ValueError, match="symbolic"):
        compare_offline_benchmark_reports([link, paths[1], paths[2]])


def test_requires_at_least_three_and_at_most_thirty_runs(tmp_path):
    paths = _cohort(tmp_path)
    with pytest.raises(ValueError, match="between 3 and 30"):
        compare_offline_benchmark_reports(paths[:2])
    with pytest.raises(ValueError, match="between 3 and 30"):
        compare_offline_benchmark_reports(paths * 11)
