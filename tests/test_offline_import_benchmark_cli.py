"""Opt-in CLI benchmark: safe output, exit codes and fresh-process entry."""
import json
import subprocess
import sys

import pytest

from mcm_solarcheck.offline import benchmark_cli as cli
from mcm_solarcheck.services.offline_import_benchmark import (
    OfflineImportBenchmarkResult,
)
from mcm_solarcheck.services.offline_import_metrics import (
    ImportPerformanceSnapshot,
)


def _result(outcome="succeeded"):
    snapshot = ImportPerformanceSnapshot(
        elapsed_seconds=2.0,
        read_and_pair_seconds=1.0,
        sqlite_commit_seconds=0.5,
        observed_progress_updates=2,
        reported_checkpoints=1,
        process_peak_rss_bytes=None,
        process_peak_rss_at_start_bytes=None,
        outcome=outcome,
    )
    return OfflineImportBenchmarkResult(
        snapshot, 1 if outcome == "succeeded" else 0, 0, 0,
    )


def test_cli_uses_local_paths_without_creating_report_by_default(
    tmp_path, monkeypatch, capsys,
):
    source = tmp_path / "SECRET-CUSTOMER-FLIGHT"
    workspace = tmp_path / "workspace"
    source.mkdir()
    workspace.mkdir()
    captured = []

    def fake_run(folder, *, workspace=None):
        captured.append((folder, workspace))
        return _result()

    monkeypatch.setattr(cli, "run_offline_import_benchmark", fake_run)
    assert cli.main([
        "--source", str(source),
        "--workspace", str(workspace),
    ]) == 0
    data = json.loads(capsys.readouterr().out)
    assert captured == [(source, workspace)]
    assert data["outcome"] == "succeeded"
    assert data["persisted_rgb_frames"] == 1
    assert data["process_peak_rss_bytes"] is None
    assert "SECRET-CUSTOMER" not in str(data)
    assert list(workspace.iterdir()) == []
    assert sorted(item.name for item in tmp_path.iterdir()) == [
        "SECRET-CUSTOMER-FLIGHT", "workspace",
    ]


def test_cli_explicit_export_is_exclusive_and_contains_no_paths(
    tmp_path, monkeypatch, capsys,
):
    source = tmp_path / "PRIVATE-SOURCE"
    source.mkdir()
    target = tmp_path / "anonyme-messung.json"
    monkeypatch.setattr(
        cli, "run_offline_import_benchmark",
        lambda *_args, **_kwargs: _result(),
    )
    command = ["--source", str(source), "--output", str(target)]
    assert cli.main(command) == 0
    content = target.read_bytes()
    payload = json.loads(content)
    assert payload["schema_version"] == 2
    assert payload["database_scope"].startswith("new_temporary")
    assert "PRIVATE-SOURCE" not in content.decode("utf-8")
    capsys.readouterr()
    assert cli.main(command) == 3
    assert target.read_bytes() == content
    text = capsys.readouterr()
    assert not text.out
    assert "PRIVATE-SOURCE" not in text.err


@pytest.mark.parametrize("outcome,expected", [
    ("succeeded", 0), ("failed", 1), ("cancelled", 130),
])
def test_cli_exit_codes_match_persisted_status_without_file_leak(
    tmp_path, monkeypatch, capsys, outcome, expected,
):
    monkeypatch.setattr(
        cli, "run_offline_import_benchmark",
        lambda *_args, **_kwargs: _result(outcome),
    )
    assert cli.main(["--source", str(tmp_path)]) == expected
    assert json.loads(capsys.readouterr().out)["outcome"] == outcome


def test_cli_does_not_print_sensitive_startup_errors(
    tmp_path, monkeypatch, capsys,
):
    def raises(*_args, **_kwargs):
        raise RuntimeError("CLIENT-SECRET-DJI_0001_T.JPG")

    monkeypatch.setattr(cli, "run_offline_import_benchmark", raises)
    assert cli.main(["--source", str(tmp_path)]) == 2
    streams = capsys.readouterr()
    assert "CLIENT-SECRET" not in streams.out + streams.err


def test_cli_can_start_in_a_separate_python_process():
    process = subprocess.run(
        [sys.executable, "-m", "mcm_solarcheck.offline.benchmark_cli", "--help"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=35, check=False,
    )
    assert process.returncode == 0, process.stderr
    assert "--source" in process.stdout
    assert "--workspace" in process.stdout
    assert "--output" in process.stdout
