"""Isolated, local-only benchmark of the real guarded offline DJI import.

Run this from a *fresh Python process* (see offline.benchmark_cli). The
reported RSS high-water mark still covers that whole process lifetime, not
just the import. This module never exports or uploads customer information.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable

from mcm_solarcheck.services.offline_import_metrics import (
    ImportPerformanceProbe,
    ImportPerformanceSnapshot,
)


@dataclass(frozen=True)
class OfflineImportBenchmarkResult:
    """An anonymous measurement of one disposable SQLite-backed import."""

    measurement: ImportPerformanceSnapshot
    rgb_frames: int
    thermal_frames: int
    image_pairs: int

    def anonymous_report(self) -> dict:
        report = self.measurement.anonymous_report()
        report.update({
            "schema_version": 2,
            "benchmark_kind": "isolated_offline_import",
            "database_scope": "new_temporary_sqlite_database_deleted_after_run",
            "rss_interpretation": "whole_fresh_process_when_run_from_cli",
            "persisted_rgb_frames": self.rgb_frames,
            "persisted_thermal_frames": self.thermal_frames,
            "persisted_image_pairs": self.image_pairs,
        })
        # A successful import is not a validated DJI field-flight acceptance.
        return report


def _existing_absolute_directory(value: str | Path, label: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or not path.is_dir():
        raise ValueError(f"{label} must be an existing absolute directory")
    return path


def run_offline_import_benchmark(
    source_directory: str | Path,
    *,
    workspace: str | Path | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> OfflineImportBenchmarkResult:
    """Import into a disposable private project and delete its SQLite DB.

    This invokes the *real* guarded importer and SQLite transaction, without
    touching an existing project DB. It does not modify source DJI files.
    Choosing a workspace only selects where the disposable DB is created.
    No benchmark report is saved here.
    """
    source = _existing_absolute_directory(source_directory, "source")
    root = (
        _existing_absolute_directory(workspace, "workspace")
        if workspace is not None else None
    )
    if root is not None and any(
        parent.is_symlink() for parent in (root, *root.parents)
    ):
        raise ValueError("workspace cannot traverse symbolic links")

    # Imports occur here to keep argument validation free of DB side effects.
    from mcm_solarcheck.services.project_pipeline import (
        ProjectApplicationService, ProjectImportCancelled,
    )
    from mcm_solarcheck.storage.sqlite import ProjectDatabase

    with TemporaryDirectory(
        prefix="solarcheck-import-benchmark-",
        dir=str(root) if root is not None else None,
    ) as temporary:
        database = ProjectDatabase(Path(temporary) / "benchmark.sqlite3")
        database.initialize()
        service = ProjectApplicationService(database)
        service.create_project("BENCHMARK", "Temporary offline benchmark")

        probe = ImportPerformanceProbe()

        def progress(phase: str, count: int) -> None:
            probe.observe(phase, count)

        try:
            attempt, _unused_result, _state = (
                service.import_project_images_cancellable(
                    "BENCHMARK", source,
                    should_cancel=should_cancel, on_progress=progress,
                )
            )
            outcome = "succeeded" if attempt.succeeded else "failed"
        except ProjectImportCancelled:
            outcome = "cancelled"
        except Exception:
            # Never let an exception containing a customer filename escape
            # into CLI diagnostics or an anonymous report.
            outcome = "failed"
        measurement = probe.finish(outcome)
        rgb = thermal = pairs = 0
        if outcome == "succeeded":
            summary = service.import_summary("BENCHMARK")
            rgb = summary.rgb_frames
            thermal = summary.thermal_frames
            pairs = summary.image_pairs

    return OfflineImportBenchmarkResult(measurement, rgb, thermal, pairs)
