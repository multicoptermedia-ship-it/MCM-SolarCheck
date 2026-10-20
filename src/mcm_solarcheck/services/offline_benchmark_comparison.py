"""Read and compare explicit local offline DJI import benchmark reports.

This is an offline, read-only analysis. Matching frame counts are not proof
that two reports processed the same source flight or ran on the same hardware.
Neither a benchmark success nor an RSS statistic is an acceptance certificate.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from statistics import median
from typing import Sequence


MAX_REPORT_BYTES = 64 * 1024
MIN_RUNS = 3
MAX_RUNS = 30

# Exactly the fields produced by OfflineImportBenchmarkResult.anonymous_report.
# Reject extensions instead of silently accepting potentially private data.
_ALLOWED = frozenset((
    "schema_version", "measurement", "outcome", "elapsed_seconds",
    "read_and_pair_seconds", "sqlite_commit_seconds", "progress_updates",
    "checkpoints_reported", "process_peak_rss_bytes",
    "process_peak_rss_at_start_bytes", "rss_scope", "sampling",
    "contains_source_paths", "contains_project_or_customer_ids",
    "is_real_dji_validation", "benchmark_kind", "database_scope",
    "rss_interpretation", "persisted_rgb_frames", "persisted_thermal_frames",
    "persisted_image_pairs",
))
_FIXED = {
    "schema_version": 2,
    "measurement": "offline_dji_import_process_observation",
    "outcome": "succeeded",
    "rss_scope": "entire_process_lifetime_not_isolated_import",
    "sampling": "phase_changes_and_coarse_progress_only",
    "contains_source_paths": False,
    "contains_project_or_customer_ids": False,
    "is_real_dji_validation": False,
    "benchmark_kind": "isolated_offline_import",
    "database_scope": "new_temporary_sqlite_database_deleted_after_run",
    "rss_interpretation": "whole_fresh_process_when_run_from_cli",
}


def _nonnegative_number(value: object, *, optional: bool = False) -> bool:
    if value is None:
        return optional
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _nonnegative_integer(value: object, *, optional: bool = False) -> bool:
    if value is None:
        return optional
    return type(value) is int and value >= 0


def _load_report(file_path: str | Path) -> dict:
    path = Path(file_path)
    if not path.is_absolute() or path.suffix.lower() != ".json":
        raise ValueError("report must have an absolute JSON path")
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError("report must not traverse symbolic links")
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_REPORT_BYTES + 1)
        if len(raw) > MAX_REPORT_BYTES:
            raise ValueError("report exceeds permitted size")
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid local benchmark report") from exc
    if type(value) is not dict or set(value) != _ALLOWED:
        raise ValueError("unexpected benchmark report fields")
    if any(value[key] != expected or type(value[key]) is not type(expected)
           for key, expected in _FIXED.items()):
        raise ValueError("unsupported benchmark report contract")
    for key in ("elapsed_seconds",):
        if not _nonnegative_number(value[key]):
            raise ValueError("invalid elapsed measurement")
    for key in ("read_and_pair_seconds", "sqlite_commit_seconds"):
        if not _nonnegative_number(value[key], optional=True):
            raise ValueError("invalid phase measurement")
    for key in ("progress_updates", "checkpoints_reported",
                "persisted_rgb_frames", "persisted_thermal_frames",
                "persisted_image_pairs"):
        if not _nonnegative_integer(value[key]):
            raise ValueError("invalid count")
    for key in ("process_peak_rss_bytes", "process_peak_rss_at_start_bytes"):
        if not _nonnegative_integer(value[key], optional=True):
            raise ValueError("invalid process RSS")
    peak = value["process_peak_rss_bytes"]
    start = value["process_peak_rss_at_start_bytes"]
    if peak is not None and start is not None and peak < start:
        raise ValueError("process peak cannot be lower than start peak")
    if not (value["persisted_rgb_frames"] or value["persisted_thermal_frames"]):
        raise ValueError("benchmark contains no persisted images")
    return value


def _stats(values: list[int | float | None], *, decimals: int = 3) -> dict | None:
    if any(value is None for value in values):
        return None
    return {
        "min": round(min(values), decimals),
        "median": round(median(values), decimals),
        "max": round(max(values), decimals),
    }


@dataclass(frozen=True)
class OfflineBenchmarkComparison:
    runs: int
    rgb_frames: int
    thermal_frames: int
    image_pairs: int
    elapsed_seconds: dict
    read_and_pair_seconds: dict | None
    sqlite_commit_seconds: dict | None
    process_peak_rss_bytes: dict | None

    def anonymous_report(self) -> dict:
        return {
            "schema_version": 1,
            "comparison_kind": "offline_dji_import_benchmark_cohort",
            "run_count": self.runs,
            "all_runs_succeeded": True,
            "persisted_rgb_frames_per_run": self.rgb_frames,
            "persisted_thermal_frames_per_run": self.thermal_frames,
            "persisted_image_pairs_per_run": self.image_pairs,
            "elapsed_seconds": self.elapsed_seconds,
            "read_and_pair_seconds": self.read_and_pair_seconds,
            "sqlite_commit_seconds": self.sqlite_commit_seconds,
            "process_peak_rss_bytes": self.process_peak_rss_bytes,
            "rss_scope": "entire_process_lifetime_not_isolated_import",
            "phase_scope": "coarse_progress_updates_not_full_profiling",
            "comparability": "counts_match_source_and_hardware_not_verified",
            "is_real_dji_validation": False,
            "is_windows_hardware_validated": False,
            "contains_source_paths": False,
            "contains_project_or_customer_ids": False,
        }


def compare_offline_benchmark_reports(
    report_paths: Sequence[str | Path],
) -> OfflineBenchmarkComparison:
    """Require 3–30 distinct successful v2 reports with identical frame counts.

    No input filenames, platform identifiers, exceptions, or unrecognized
    report content are carried into the comparison result.
    """
    if not MIN_RUNS <= len(report_paths) <= MAX_RUNS:
        raise ValueError("need between 3 and 30 reports")
    normalized = [Path(path) for path in report_paths]
    # Normalize Windows path casing when comparing on Windows.
    import os
    identities = [os.path.normcase(str(path.resolve(strict=False))) for path in normalized]
    if len(set(identities)) != len(identities):
        raise ValueError("duplicate benchmark report")
    records = [_load_report(path) for path in normalized]
    counts = [
        (item["persisted_rgb_frames"], item["persisted_thermal_frames"],
         item["persisted_image_pairs"])
        for item in records
    ]
    if len(set(counts)) != 1:
        raise ValueError("persisted frame counts differ across reports")
    rgb, thermal, pairs = counts[0]
    return OfflineBenchmarkComparison(
        runs=len(records),
        rgb_frames=rgb, thermal_frames=thermal, image_pairs=pairs,
        elapsed_seconds=_stats([x["elapsed_seconds"] for x in records]),
        read_and_pair_seconds=_stats(
            [x["read_and_pair_seconds"] for x in records],
        ),
        sqlite_commit_seconds=_stats(
            [x["sqlite_commit_seconds"] for x in records],
        ),
        process_peak_rss_bytes=_stats(
            [x["process_peak_rss_bytes"] for x in records], decimals=0,
        ),
    )
