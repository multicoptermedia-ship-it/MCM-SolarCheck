"""The offline asynchronous import boundary is project-scoped and atomic."""
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import pytest

import mcm_solarcheck.services.project_pipeline as pipeline
from mcm_solarcheck.domain.models import Finding, ImageFrame, ImagePair, ThermalFrame
from mcm_solarcheck.importers.project import ProjectImportResult
from mcm_solarcheck.services.project_pipeline import (
    ProjectApplicationService, ProjectImportCancelled,
)
from mcm_solarcheck.services.workflow import WorkflowAction
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult


def service(tmp_path):
    db = ProjectDatabase(tmp_path / "offline.sqlite3")
    db.initialize()
    db.create_project("P1", "Dach Nord")
    db.create_project("P2", "Dach Sued")
    return ProjectApplicationService(db)


def sample_import(*, broken_thermal=False, empty=False):
    if empty:
        return ProjectImportResult((), SimpleNamespace(results=(), failures=()), ())
    rgb = tuple(
        ImageFrame(f"V-{i}", Path(f"DJI_{i:04d}_V.JPG"))
        for i in range(3)
    )
    frame = ThermalFrame(
        frame_id="T-1", source_file=Path("DJI_0001_T.JPG"),
        thermal_width=640, thermal_height=512, thermal_source="raw",
    )
    quality = ThermalQualityResult(
        ThermalQualityGrade.PASS, (),
        RawThermalStatistics(1, 10, 5.0, 5.0, 9.0, 10.0, 9),
    )
    result = SimpleNamespace(
        frame=frame, quality=quality,
        findings=(Finding("F-1", "T-1", 3, 4),),
    )
    failures = (
        (SimpleNamespace(source_file=Path("bad_T.JPG"), error_type="ValueError",
                         message="unreadable"),)
        if broken_thermal else ()
    )
    batch = SimpleNamespace(results=(result,), failures=failures)
    pairs = (ImagePair("PAIR-1", "V-1", "T-1", 0.9, "sequence+time"),)
    return ProjectImportResult(rgb, batch, pairs)


def assert_empty(service_instance):
    for project in ("P1", "P2"):
        s = service_instance.import_summary(project)
        assert (s.rgb_frames, s.thermal_frames, s.image_pairs, s.findings) == (0, 0, 0, 0)


def test_successful_import_commits_rgb_thermal_findings_pairs_together(monkeypatch, tmp_path):
    app = service(tmp_path)
    calls = []

    def importer(directory, **kwargs):
        assert str(directory) == "flight"
        heartbeat = kwargs["heartbeat"]
        for _ in range(4):
            heartbeat()
        return sample_import()

    monkeypatch.setattr(pipeline, "import_m3t_project", importer)
    attempt, data, state = app.import_project_images_cancellable(
        "P1", "flight", on_progress=lambda phase, count: calls.append((phase, count)),
    )
    assert attempt.action is WorkflowAction.IMPORT
    assert attempt.succeeded
    assert data[1].rgb_frames == 3
    assert data[1].thermal_frames == 1
    assert data[1].pairs == 1
    assert data[1].findings == 1
    assert state is not None
    s = app.import_summary("P1")
    assert (s.rgb_frames, s.thermal_frames, s.image_pairs, s.findings) == (3, 1, 1, 1)
    assert app.import_summary("P2").rgb_frames == 0
    assert calls[0] == ("Einlesen und Zuordnen", 0)
    assert ("Atomare SQLite-Speicherung", 0) in calls
    assert sorted((x.project_id, x.name) for x in app.projects()) == [
        ("P1", "Dach Nord"), ("P2", "Dach Sued"),
    ]


def test_cancel_during_decode_never_changes_sqlite(monkeypatch, tmp_path):
    app = service(tmp_path)
    stop = Event()

    def importer(_folder, **kwargs):
        kwargs["heartbeat"]()
        stop.set()
        kwargs["heartbeat"]()
        raise AssertionError("should have aborted")

    monkeypatch.setattr(pipeline, "import_m3t_project", importer)
    with pytest.raises(ProjectImportCancelled):
        app.import_project_images_cancellable(
            "P1", "flight", should_cancel=stop.is_set,
        )
    assert_empty(app)


def test_cancel_during_sqlite_transaction_rolls_back_prior_writes(monkeypatch, tmp_path):
    app = service(tmp_path)
    monkeypatch.setattr(pipeline, "import_m3t_project", lambda *a, **k: sample_import())
    original_save = app.database.save_project_import
    n = 0

    def interrupted_save(project_id, imported, *, checkpoint=None):
        def stop_mid_transaction():
            nonlocal n
            n += 1
            if n == 4:
                raise ProjectImportCancelled("cancel during sqlite save")
            if checkpoint is not None:
                checkpoint()
        return original_save(project_id, imported, checkpoint=stop_mid_transaction)

    monkeypatch.setattr(app.database, "save_project_import", interrupted_save)
    with pytest.raises(ProjectImportCancelled, match="sqlite save"):
        app.import_project_images_cancellable("P1", "flight")
    assert n == 4
    assert_empty(app)
    with app.database.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM training_samples").fetchone()[0] == 0


def test_unreadable_thermal_image_fails_closed_before_writes(monkeypatch, tmp_path):
    app = service(tmp_path)
    monkeypatch.setattr(
        pipeline, "import_m3t_project",
        lambda *args, **kwargs: sample_import(broken_thermal=True),
    )
    attempt, result, _state = app.import_project_images_cancellable("P1", "flight")
    assert not attempt.succeeded
    assert "Thermaldateien" in attempt.error
    assert result is None
    assert_empty(app)


def test_empty_import_is_failure_not_false_success(monkeypatch, tmp_path):
    app = service(tmp_path)
    monkeypatch.setattr(
        pipeline, "import_m3t_project",
        lambda *args, **kwargs: sample_import(empty=True),
    )
    attempt, result, _state = app.import_project_images_cancellable("P1", "flight")
    assert not attempt.succeeded
    assert "Keine importierbaren DJI-Bilder" in attempt.error
    assert result is None
    assert_empty(app)


def test_sqlite_failure_rolls_back_entire_import(monkeypatch, tmp_path):
    app = service(tmp_path)
    monkeypatch.setattr(pipeline, "import_m3t_project", lambda *a, **k: sample_import())
    def fail_after_rgb(*a, **k):
        raise OSError("simulated disk failure")
    monkeypatch.setattr(app.database, "_save_thermal_frame", fail_after_rgb)
    attempt, result, _state = app.import_project_images_cancellable("P1", "flight")
    assert not attempt.succeeded
    assert "simulated disk failure" in attempt.error
    assert result is None
    assert_empty(app)


def test_cancel_before_read_and_unknown_project_do_not_invoke_import(monkeypatch, tmp_path):
    app = service(tmp_path)
    invoked = []
    monkeypatch.setattr(
        pipeline, "import_m3t_project",
        lambda *a, **k: invoked.append(True),
    )
    with pytest.raises(ProjectImportCancelled):
        app.import_project_images_cancellable(
            "P1", "flight", should_cancel=lambda: True,
        )
    with pytest.raises(KeyError):
        app.import_project_images_cancellable("missing", "flight")
    assert invoked == []
    assert_empty(app)


def test_legacy_sync_import_reuses_existing_project_and_atomic_commit(monkeypatch, tmp_path):
    app = service(tmp_path)
    calls = []
    def importer(directory, **kwargs):
        calls.append((str(directory), kwargs["retain_rasters"]))
        return sample_import()
    monkeypatch.setattr(pipeline, "import_m3t_project", importer)
    attempt, imported, state = app.import_project_images("P1", "legacy-flight")
    assert attempt.succeeded
    assert imported[1].rgb_frames == 3
    assert imported[1].thermal_frames == 1
    assert calls == [("legacy-flight", False)]
    assert sorted((project.project_id, project.name) for project in app.projects()) == [
        ("P1", "Dach Nord"), ("P2", "Dach Sued"),
    ]
    assert app.import_summary("P1").image_pairs == 1
    assert app.import_summary("P2").image_pairs == 0


def test_legacy_sync_import_failure_does_not_write_partial_evidence(monkeypatch, tmp_path):
    app = service(tmp_path)
    def importer(directory, **kwargs):
        return sample_import(broken_thermal=True)
    monkeypatch.setattr(pipeline, "import_m3t_project", importer)
    attempt, imported, _state = app.import_project_images("P1", "legacy-flight")
    assert not attempt.succeeded
    assert imported is None
    assert_empty(app)
