"""Vertical local CLI comparison: no overwrite, no private output, no network."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from mcm_solarcheck.offline import benchmark_compare_cli as cli
from mcm_solarcheck.services.offline_import_benchmark import (
    OfflineImportBenchmarkResult,
)
from mcm_solarcheck.services.offline_import_metrics import ImportPerformanceSnapshot


def _reports(tmp_path):
    source = tmp_path / "PRIVATE-CUSTOMER-FOLDER"
    source.mkdir()
    paths = [source / f"PRIVATE-CUSTOMER-RUN-{i}.json" for i in range(3)]
    for index, path in enumerate(paths):
        measurement = ImportPerformanceSnapshot(
            elapsed_seconds=float(index + 1),
            read_and_pair_seconds=0.5,
            sqlite_commit_seconds=0.25,
            observed_progress_updates=2, reported_checkpoints=3,
            process_peak_rss_bytes=None if index == 0 else (index + 2) * 2048,
            process_peak_rss_at_start_bytes=None if index == 0 else 1024,
            outcome="succeeded",
        )
        report = OfflineImportBenchmarkResult(
            measurement, 3, 2, 2,
        ).anonymous_report()
        path.write_text(json.dumps(report), encoding="utf-8")
    return paths


def test_cli_compares_without_writing_and_does_not_reveal_names(
    tmp_path, capsys,
):
    paths = _reports(tmp_path)
    assert cli.main(["--reports", *map(str, paths)]) == 0
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["run_count"] == 3
    assert output["elapsed_seconds"]["median"] == 2.0
    assert output["process_peak_rss_bytes"] is None
    assert output["is_real_dji_validation"] is False
    assert captured.err == ""
    assert "PRIVATE-CUSTOMER" not in captured.out
    assert len(list(paths[0].parent.iterdir())) == 3


def test_explicit_export_is_non_overwriting_and_anonymized(
    tmp_path, capsys,
):
    paths = _reports(tmp_path)
    destination = tmp_path / "comparison.json"
    argv = ["--reports", *map(str, paths), "--output", str(destination)]
    assert cli.main(argv) == 0
    saved = destination.read_bytes()
    report = json.loads(saved)
    assert report["run_count"] == 3
    assert report["contains_project_or_customer_ids"] is False
    assert "PRIVATE-CUSTOMER" not in saved.decode("utf-8")
    capsys.readouterr()
    assert cli.main(argv) == 3
    captured = capsys.readouterr()
    assert not captured.out
    assert "PRIVATE-CUSTOMER" not in captured.err
    assert destination.read_bytes() == saved


@pytest.mark.parametrize("change", [
    lambda p: [p[0], p[1]],
    lambda p: [p[0], p[0], p[2]],
])
def test_invalid_sets_fail_without_path_disclosure(tmp_path, capsys, change):
    paths = _reports(tmp_path)
    assert cli.main(["--reports", *map(str, change(paths))]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PRIVATE-CUSTOMER" not in captured.err


def test_extra_private_field_rejected_without_echo(tmp_path, capsys):
    paths = _reports(tmp_path)
    report = json.loads(paths[0].read_text(encoding="utf-8"))
    report["secret_input_file"] = "VERY-PRIVATE-DJI-FILE.JPG"
    paths[0].write_text(json.dumps(report), encoding="utf-8")
    assert cli.main(["--reports", *map(str, paths)]) == 2
    captured = capsys.readouterr()
    assert "VERY-PRIVATE" not in captured.err + captured.out
    assert "PRIVATE-CUSTOMER" not in captured.err + captured.out


def test_comparison_cli_help_starts_in_separate_python_process():
    process = subprocess.run(
        [sys.executable, "-m",
         "mcm_solarcheck.offline.benchmark_compare_cli", "--help"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=35, check=False,
    )
    assert process.returncode == 0, process.stderr
    assert "--reports" in process.stdout
    assert "--output" in process.stdout
