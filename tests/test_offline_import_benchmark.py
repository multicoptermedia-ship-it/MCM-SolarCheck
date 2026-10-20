"""Disposable SQLite benchmark: import outcomes, privacy and cleanup."""
from pathlib import Path
from types import SimpleNamespace

import pytest

import mcm_solarcheck.services.project_pipeline as pipeline
from mcm_solarcheck.domain.models import ImageFrame
from mcm_solarcheck.importers.project import ProjectImportResult
from mcm_solarcheck.services.offline_import_benchmark import (
    run_offline_import_benchmark,
)


def _fake_rgb_import(_directory, *, heartbeat=None, **_kwargs):
    if heartbeat is not None:
        heartbeat()
    return ProjectImportResult(
        (ImageFrame("RGB-1", Path("KUNDE-PRIVAT-DJI_0001_V.JPG")),),
        SimpleNamespace(results=(), failures=()),
        (),
    )


def test_benchmark_uses_disposable_sqlite_and_retains_no_filenames(
    tmp_path, monkeypatch,
):
    source = tmp_path / "PRIVATE-CLIENT-MAVIC"
    workspace = tmp_path / "working"
    source.mkdir()
    workspace.mkdir()
    original = source / "DJI_0001_V.JPG"
    original.write_bytes(b"DO-NOT-TOUCH")
    observed = []

    def importer(path, **kwargs):
        observed.append(path)
        return _fake_rgb_import(path, **kwargs)

    monkeypatch.setattr(pipeline, "import_m3t_project", importer)
    result = run_offline_import_benchmark(source, workspace=workspace)

    assert observed == [source]
    assert result.measurement.outcome == "succeeded"
    assert result.rgb_frames == 1
    assert result.thermal_frames == 0
    assert result.image_pairs == 0
    assert result.measurement.elapsed_seconds >= 0
    assert original.read_bytes() == b"DO-NOT-TOUCH"
    assert list(workspace.iterdir()) == []
    report = result.anonymous_report()
    assert report["schema_version"] == 2
    assert report["persisted_rgb_frames"] == 1
    assert report["outcome"] == "succeeded"
    assert report["contains_source_paths"] is False
    assert report["is_real_dji_validation"] is False
    assert "PRIVATE-CLIENT" not in str(report)
    assert "KUNDE-PRIVAT" not in str(report)
    assert "benchmark.sqlite3" not in str(report)


def test_failed_import_emits_no_private_exception_and_cleans_up(
    tmp_path, monkeypatch,
):
    source = tmp_path / "source"
    workspace = tmp_path / "tempdb"
    source.mkdir()
    workspace.mkdir()

    def importer(*_args, **_kwargs):
        raise ValueError("PRIVATE-CUSTOMER-NAME.JPG could not be parsed")

    monkeypatch.setattr(pipeline, "import_m3t_project", importer)
    result = run_offline_import_benchmark(source, workspace=workspace)

    assert result.measurement.outcome == "failed"
    assert result.rgb_frames == result.thermal_frames == result.image_pairs == 0
    assert "PRIVATE-CUSTOMER" not in str(result.anonymous_report())
    assert list(workspace.iterdir()) == []


def test_cancelled_benchmark_cleans_up_without_claiming_success(
    tmp_path, monkeypatch,
):
    source = tmp_path / "source"
    workspace = tmp_path / "work"
    source.mkdir()
    workspace.mkdir()

    def never_import(*_args, **_kwargs):
        raise AssertionError("import must not start after cancellation")

    monkeypatch.setattr(pipeline, "import_m3t_project", never_import)
    result = run_offline_import_benchmark(
        source, workspace=workspace, should_cancel=lambda: True,
    )
    assert result.measurement.outcome == "cancelled"
    assert result.rgb_frames == 0
    assert list(workspace.iterdir()) == []


def test_benchmark_rejects_invalid_directories_without_db_creation(tmp_path):
    source = tmp_path / "source"
    workspace = tmp_path / "workspace"
    source.mkdir()
    workspace.mkdir()

    with pytest.raises(ValueError, match="absolute"):
        run_offline_import_benchmark("relative")
    with pytest.raises(ValueError, match="absolute"):
        run_offline_import_benchmark(source, workspace=Path("relative"))
    with pytest.raises(ValueError, match="existing absolute"):
        run_offline_import_benchmark(tmp_path / "nonexistent", workspace=workspace)
    assert list(workspace.iterdir()) == []


def test_benchmark_rejects_symlinked_workspace(tmp_path):
    source = tmp_path / "source"
    root = tmp_path / "real"
    linked = tmp_path / "linked"
    source.mkdir()
    root.mkdir()
    try:
        linked.symlink_to(root, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links unsupported")
    with pytest.raises(ValueError, match="symbolic"):
        run_offline_import_benchmark(source, workspace=linked)
    assert list(root.iterdir()) == []
