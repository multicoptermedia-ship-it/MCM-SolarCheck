"""Deterministic, privacy-preserving offline import measurement contracts."""
import json
from pathlib import Path

import pytest

from mcm_solarcheck.services.offline_import_metrics import (
    ImportPerformanceProbe, ImportPerformanceSnapshot,
    format_import_performance, save_anonymous_import_report,
)


def samples(values):
    data = iter(values)
    return lambda: next(data)


def test_stage_durations_and_process_lifetime_peak_are_measured_separately():
    observer = ImportPerformanceProbe(
        clock_ns=samples((0, 2_000_000_000, 5_000_000_000,
                          9_000_000_000, 13_000_000_000)),
        peak_rss=samples((1_024, 2_048, 4_096, 8_192, 4_096)),
    )
    observer.observe("Einlesen und Zuordnen", 0)
    observer.observe("Einlesen und Zuordnen", 50)
    observer.observe("Atomare SQLite-Speicherung", 0)
    final = observer.finish("succeeded")
    assert final.elapsed_seconds == 13.0
    assert final.read_and_pair_seconds == 7.0
    assert final.sqlite_commit_seconds == 4.0
    assert final.observed_progress_updates == 3
    assert final.reported_checkpoints == 50
    assert final.process_peak_rss_at_start_bytes == 1_024
    assert final.process_peak_rss_bytes == 8_192
    assert final.anonymous_report()["rss_scope"] == (
        "entire_process_lifetime_not_isolated_import"
    )
    with pytest.raises(RuntimeError, match="finalized"):
        observer.observe("Einlesen und Zuordnen", 100)
    with pytest.raises(RuntimeError, match="finalized"):
        observer.finish("succeeded")


@pytest.mark.parametrize("outcome", ["failed", "cancelled"])
def test_cancel_and_failure_are_observed_without_fake_phase_measurements(outcome):
    observer = ImportPerformanceProbe(
        clock_ns=samples((10, 3_000_000_010)),
        peak_rss=samples((None, None)),
    )
    final = observer.finish(outcome)
    assert final.outcome == outcome
    assert final.elapsed_seconds == 3.0
    assert final.read_and_pair_seconds is None
    assert final.sqlite_commit_seconds is None
    assert final.process_peak_rss_bytes is None
    assert "nicht verfügbar" in format_import_performance(final)


def test_unknown_progress_phase_cannot_leak_customer_file_names():
    private_name = "PRIVATER-KUNDE-SOLARFELD.JPG"
    observer = ImportPerformanceProbe(
        clock_ns=samples((0, 1_000_000_000, 2_000_000_000)),
        peak_rss=samples((1_000, 1_000, 1_000)),
    )
    observer.observe(private_name, 5)
    final = observer.finish("succeeded")
    assert private_name not in str(final)
    assert private_name not in str(final.anonymous_report())
    assert private_name not in format_import_performance(final)


def test_export_is_opt_in_anonymous_versioned_and_exclusive(tmp_path):
    snapshot = ImportPerformanceSnapshot(
        elapsed_seconds=2.123456, read_and_pair_seconds=1.125,
        sqlite_commit_seconds=0.9, observed_progress_updates=3,
        reported_checkpoints=100, process_peak_rss_bytes=12_345_678,
        process_peak_rss_at_start_bytes=10_000_000,
        outcome="succeeded",
    )
    destination = tmp_path / "PRIVATER-KUNDE.json"
    assert save_anonymous_import_report(snapshot, destination) == destination
    content = destination.read_text(encoding="utf-8")
    document = json.loads(content)
    assert document["schema_version"] == 1
    assert document["elapsed_seconds"] == 2.123
    assert document["read_and_pair_seconds"] == 1.125
    assert document["outcome"] == "succeeded"
    assert document["contains_source_paths"] is False
    assert document["contains_project_or_customer_ids"] is False
    assert "PRIVATER-KUNDE" not in content
    assert "Mavic" not in content
    with pytest.raises(FileExistsError):
        save_anonymous_import_report(snapshot, destination)
    assert content == destination.read_text(encoding="utf-8")


def test_diagnostic_export_rejects_unsafe_paths_before_write(tmp_path):
    snapshot = ImportPerformanceProbe(
        clock_ns=samples((0, 1)),
        peak_rss=samples((None, None)),
    ).finish("failed")
    with pytest.raises(ValueError, match="JSON"):
        save_anonymous_import_report(snapshot, tmp_path / "unwanted.pdf")
    with pytest.raises(ValueError, match="absolute"):
        save_anonymous_import_report(snapshot, "relative.json")
    with pytest.raises(ValueError, match="directory"):
        save_anonymous_import_report(snapshot, tmp_path / "missing" / "report.json")
    assert not (tmp_path / "unwanted.pdf").exists()

    (tmp_path / "real").mkdir()
    try:
        (tmp_path / "linked").symlink_to(tmp_path / "real", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported")
    with pytest.raises(ValueError, match="symlinks"):
        save_anonymous_import_report(snapshot, tmp_path / "linked" / "report.json")
    assert not (tmp_path / "real" / "report.json").exists()


@pytest.mark.parametrize("outcome", ["ok", "", "aborted"])
def test_unknown_outcome_is_rejected(outcome):
    observer = ImportPerformanceProbe(
        clock_ns=samples((0,)),
        peak_rss=samples((None,)),
    )
    with pytest.raises(ValueError, match="outcome"):
        observer.finish(outcome)


def test_formatted_metrics_explicitly_disclaim_isolated_peak():
    snapshot = ImportPerformanceSnapshot(
        elapsed_seconds=9.5, read_and_pair_seconds=6.0,
        sqlite_commit_seconds=3.2, observed_progress_updates=3,
        reported_checkpoints=50, process_peak_rss_bytes=20 * 1024 * 1024,
        process_peak_rss_at_start_bytes=15 * 1024 * 1024,
        outcome="succeeded",
    )
    message = format_import_performance(snapshot)
    assert "20.0 MiB" in message
    assert "9.5 s" in message
    assert "keine isolierte Importspitze" in message
    assert "keine" in message.lower()
