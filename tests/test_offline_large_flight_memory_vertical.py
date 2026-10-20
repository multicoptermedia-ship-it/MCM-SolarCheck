"""Offline large-flight memory regression: real service -> importer -> SQLite -> Qt."""
from __future__ import annotations

import gc
from pathlib import Path
from types import SimpleNamespace
import weakref

import pytest

from mcm_solarcheck.domain.models import Finding, ThermalFrame
from mcm_solarcheck.importers.m3t import M3TImportResult
from mcm_solarcheck.services.project_pipeline import ProjectApplicationService
from mcm_solarcheck.services.workflow import WorkflowAction, record_attempt
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.m3t_radiometric import RadiometricRaster
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult


def test_offline_120_thermal_frames_release_raw_rasters_and_persist_evidence(
    tmp_path, monkeypatch,
):
    import mcm_solarcheck.importers.batch as batch_module

    db = ProjectDatabase(tmp_path / "project.sqlite3")
    db.initialize()
    db.create_project("P1", "PV-Park Nord")
    db.create_project("P2", "PV-Park Sued")
    source = tmp_path / "flight"
    source.mkdir()
    for i in range(120):
        (source / f"DJI_20261020_{i:04d}_T.JPG").touch()
    refs = []

    class GeneratedThermalImporter:
        def import_file(self, path, *, candidate_percentile=99.9, candidate_limit=100):
            index = int(Path(path).stem.split("_")[-2])
            frame = ThermalFrame(
                frame_id=f"T-{index:04d}", source_file=Path(path),
                thermal_width=640, thermal_height=512, thermal_source="DJI M3T APP3 raw",
            )
            raster = RadiometricRaster(
                640, 512, "little", (19000 + index,) * (640 * 512), 0,
            )
            refs.append(weakref.ref(raster))
            quality = ThermalQualityResult(
                ThermalQualityGrade.PASS, (),
                RawThermalStatistics(
                    19000 + index, 19000 + index, 19000.0 + index,
                    19000.0 + index, 19000.0 + index,
                    19000.0 + index, 0,
                ),
            )
            return M3TImportResult(
                frame=frame, raster=raster, quality=quality, candidates=(),
                findings=(Finding(
                    f"F-{index:04d}", frame.frame_id, 2, 3,
                    raw_value=19000 + index,
                ),),
                xmp=SimpleNamespace(raw={}),
            )

    monkeypatch.setattr(batch_module, "M3TImporter", GeneratedThermalImporter)
    service = ProjectApplicationService(db)
    progress = []
    attempt, data, state = service.import_project_images_cancellable(
        "P1", source, on_progress=lambda phase, count: progress.append(
            (phase, count)
        ),
    )
    assert attempt.action is WorkflowAction.IMPORT
    assert attempt.succeeded
    imported, summary = data
    assert summary.rgb_frames == 0
    assert summary.thermal_frames == 120
    assert summary.thermal_failures == 0
    assert summary.findings == 120
    assert len(imported.thermal_batch.results) == 120
    assert all(result.raster is None for result in imported.thermal_batch.results)
    assert all(len(result.findings) == 1 for result in imported.thermal_batch.results)
    assert all(
        result.findings[0].temperature_c is None
        for result in imported.thermal_batch.results
    )
    assert ("Atomare SQLite-Speicherung", 0) in progress
    stored = service.import_summary("P1")
    assert stored.thermal_frames == 120
    assert stored.findings == 120
    assert stored.unreviewed_findings == 120
    assert stored.calibrated_findings == 0
    assert service.import_summary("P2").thermal_frames == 0
    assert len(refs) == 120
    gc.collect()
    assert all(ref() is None for ref in refs), (
        "large raw sample arrays were retained after offline persistence"
    )
    assert state is not None


def test_qt_worker_signal_does_not_transfer_bulk_import_objects():
    pytest.importorskip("PySide6")
    from mcm_solarcheck.gui.flight_import_worker import FlightImportThread

    references = []

    class BulkPayload:
        pass

    class StubService:
        def import_project_images_cancellable(
            self, project_id, source_folder, *, should_cancel=None, on_progress=None,
        ):
            assert project_id == "P1"
            assert source_folder == "flight"
            bulk = BulkPayload()
            references.append(weakref.ref(bulk))
            return (
                record_attempt(WorkflowAction.IMPORT),
                (bulk, SimpleNamespace(thermal_frames=120)),
                SimpleNamespace(project_id=project_id),
            )

    worker = FlightImportThread(StubService(), "P1", "flight")
    delivered = []
    worker.result_ready.connect(delivered.append)
    worker.run()  # Execute the signal contract directly; thread lifecycle is tested separately.
    assert len(delivered) == 1
    attempt, payload, state = delivered[0]
    assert attempt.succeeded
    assert payload is None
    assert state.project_id == "P1"
    gc.collect()
    assert references[0]() is None, (
        "Qt worker still holds a full batch after emitting the completion signal"
    )
