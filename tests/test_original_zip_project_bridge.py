"""End-to-end bridge: original ZIPs -> durable private files -> existing SQLite project.

All fixtures are synthesized: no original customer images in GitHub tests.
"""
from __future__ import annotations

from dataclasses import replace
from io import BytesIO
import json
import os
from pathlib import Path
from threading import Event
from types import SimpleNamespace
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PIL import Image
from PySide6.QtWidgets import QApplication, QPushButton, QCheckBox

import mcm_solarcheck.services.project_pipeline as pipeline
from mcm_solarcheck.gui.import_page import make_import_page
from mcm_solarcheck.importers.project import ProjectImportResult
from mcm_solarcheck.services.project_pipeline import ProjectApplicationService, ProjectImportCancelled
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from test_offline_cancellable_import import sample_import


def fixture_image(size):
    exif = Image.Exif()
    exif[271] = "DJI"
    exif[272] = "M3T"
    exif[306] = "2025:08:25 12:16:42"
    buf = BytesIO()
    Image.new("RGB", size, (40, 60, 70)).save(buf, "JPEG", exif=exif)
    return buf.getvalue()


def zip_pair(tmp_path):
    thermal, rgb = tmp_path / "thermal.zip", tmp_path / "rgb.zip"
    a, b = fixture_image((640, 512)), fixture_image((4000, 3000))
    with zipfile.ZipFile(thermal, "w") as z:
        z.writestr("DJI_20250825121642_0128_T.JPG", a)
        z.writestr("DJI_20250825121642_0129_T.JPG", a)
    with zipfile.ZipFile(rgb, "w") as z:
        z.writestr("DJI_20250825121642_0128_V.JPG", b)
    return thermal, rgb


def project(tmp_path):
    db = ProjectDatabase(tmp_path / "private.sqlite3")
    db.initialize()
    db.create_project("PV1", "Local pilot")
    db.create_project("PV2", "Unrelated project")
    return ProjectApplicationService(db)


def fake_import_in_durable_folder(folder, **kwargs):
    base = Path(folder)
    expected = (
        "DJI_20250825121642_0128_T.JPG",
        "DJI_20250825121642_0128_V.JPG",
    )
    assert all((base / file).is_file() for file in expected)
    original = sample_import()
    rgb = tuple(
        replace(frame, source_file=base / expected[1])
        for frame in original.rgb_frames
    )
    thermal = tuple(
        replace(item, frame=replace(item.frame, source_file=base / expected[0]))
        for item in original.thermal_batch.results
    )
    batch = SimpleNamespace(results=thermal, failures=())
    return ProjectImportResult(rgb, batch, original.pairs)


def test_original_zips_import_into_existing_project_and_preserve_private_paths(
    tmp_path, monkeypatch,
):
    service = project(tmp_path)
    zips = zip_pair(tmp_path)
    original_bytes = [p.read_bytes() for p in zips]
    monkeypatch.setattr(pipeline, "import_m3t_project", fake_import_in_durable_folder)
    events = []
    attempt, imported, _state = service.import_project_original_zips_cancellable(
        "PV1", *zips, on_progress=lambda phase, count: events.append((phase, count)),
    )
    assert attempt.succeeded
    assert imported[1].pairs == 1
    summary = service.import_summary("PV1")
    assert (summary.rgb_frames, summary.thermal_frames, summary.image_pairs) == (3, 1, 1)
    assert service.import_summary("PV2").thermal_frames == 0
    folders = list((tmp_path / "private-m3t-originals").iterdir())
    assert len(folders) == 1
    folder = folders[0]
    assert (folder / "DJI_20250825121642_0128_T.JPG").is_file()
    assert (folder / "DJI_20250825121642_0128_V.JPG").is_file()
    assert not (folder / "DJI_20250825121642_0129_T.JPG").exists()
    assert any(item[0] == "Unveränderte Originale sichern" for item in events)
    assert [p.read_bytes() for p in zips] == original_bytes
    assert len(service.projects()) == 2
    manifest = json.loads((folder / "m3t-original-provenance.json").read_text())
    assert not any(x["training_rights_approved"] for x in manifest["files"])
    assert not any(x["human_reviewed"] for x in manifest["files"])


def test_failed_sqlite_import_removes_only_new_staging_and_leaves_originals(
    tmp_path, monkeypatch,
):
    service = project(tmp_path)
    zips = zip_pair(tmp_path)
    original = [z.read_bytes() for z in zips]
    monkeypatch.setattr(
        pipeline, "import_m3t_project", lambda *a, **k: sample_import(broken_thermal=True),
    )
    attempt, imported, _ = service.import_project_original_zips_cancellable(
        "PV1", *zips,
    )
    assert not attempt.succeeded
    assert imported is None
    assert service.import_summary("PV1").thermal_frames == 0
    assert service.import_summary("PV2").rgb_frames == 0
    root = tmp_path / "private-m3t-originals"
    assert list(root.iterdir()) == []
    assert [p.read_bytes() for p in zips] == original


def test_cancel_during_staging_keeps_database_empty_and_avoids_leaked_copies(
    tmp_path, monkeypatch,
):
    service = project(tmp_path)
    zips = zip_pair(tmp_path)
    cancel = Event()
    def progress(phase, number):
        if phase == "Unveränderte Originale sichern":
            cancel.set()
    monkeypatch.setattr(
        pipeline, "import_m3t_project",
        lambda *a, **k: pytest.fail("decoder cannot run after cancellation"),
    )
    with pytest.raises(ProjectImportCancelled):
        service.import_project_original_zips_cancellable(
            "PV1", *zips, should_cancel=cancel.is_set, on_progress=progress,
        )
    assert service.import_summary("PV1").thermal_frames == 0
    assert list((tmp_path / "private-m3t-originals").iterdir()) == []


def test_already_imported_project_refuses_second_zip_import_before_staging(
    tmp_path, monkeypatch,
):
    service = project(tmp_path)
    zips = zip_pair(tmp_path)
    monkeypatch.setattr(pipeline, "import_m3t_project", fake_import_in_durable_folder)
    assert service.import_project_original_zips_cancellable("PV1", *zips)[0].succeeded
    with pytest.raises(PermissionError, match="empty"):
        service.import_project_original_zips_cancellable("PV1", *zips)
    assert len(list((tmp_path / "private-m3t-originals").iterdir())) == 1


def test_original_zip_gui_requires_project_and_intent_to_include_thermal_only(tmp_path):
    app = QApplication.instance() or QApplication([])
    actions = []
    page = make_import_page(
        current_project_id="PV1",
        on_import_original_zips=lambda t, v, extra: actions.append((t, v, extra)),
        choose_thermal_zip=lambda: "/local/thermal.zip",
        choose_rgb_zip=lambda: "/local/rgb.zip",
    )
    try:
        button = page.findChild(QPushButton, "import_original_zips_button")
        toggle = page.findChild(QCheckBox, "import_original_thermal_only_choice")
        assert button.isEnabled()
        assert not toggle.isChecked()
        button.click()
        toggle.setChecked(True)
        button.click()
        assert actions == [
            ("/local/thermal.zip", "/local/rgb.zip", False),
            ("/local/thermal.zip", "/local/rgb.zip", True),
        ]
    finally:
        page.close()
    unavailable = make_import_page(current_project_id=None)
    try:
        assert not unavailable.findChild(QPushButton, "import_original_zips_button").isEnabled()
    finally:
        unavailable.close()


def test_unrecognized_modality_or_original_zip_does_not_mutate_project(tmp_path):
    service = project(tmp_path)
    t, v = zip_pair(tmp_path)
    with zipfile.ZipFile(v, "a") as z:
        z.writestr("../not-original.JPG", b"untrusted")
    with pytest.raises(PermissionError):
        service.import_project_original_zips_cancellable("PV1", t, v)
    assert service.import_summary("PV1").rgb_frames == 0
    assert not list((tmp_path / "private-m3t-originals").glob("*"))


def test_original_zip_worker_dispatches_explicit_mode_without_training(tmp_path):
    from mcm_solarcheck.gui.flight_import_worker import FlightImportThread
    class FakeService:
        def import_project_original_zips_cancellable(self, project_id, t, v, **kw):
            assert (project_id, t, v) == ("PV1", "thermal.zip", "rgb.zip")
            assert kw["include_unpaired_thermal"] is True
            return (SimpleNamespace(succeeded=True), None, "state")
        def import_project_images_cancellable(self, *_a, **_kw):
            pytest.fail("regular directory importer must not be invoked")
    app = QApplication.instance() or QApplication([])
    thread = FlightImportThread(
        FakeService(), "PV1", "",
        original_zips=("thermal.zip", "rgb.zip"), include_unpaired_thermal=True,
    )
    outcomes = []
    thread.result_ready.connect(lambda value: outcomes.append(value))
    thread.run()
    assert len(outcomes) == 1
    assert outcomes[0][0].succeeded is True
