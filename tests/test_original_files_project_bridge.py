"""The primary offline import accepts unpacked DJI M3T files, never requires ZIP.

Fixtures are synthesized; no customer photos or coordinates enter CI.
"""
from __future__ import annotations

from io import BytesIO
import json
import os
from pathlib import Path
from threading import Event
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PIL import Image
from PySide6.QtWidgets import QApplication, QPushButton

from mcm_solarcheck.gui.import_page import make_import_page
from mcm_solarcheck.gui.flight_import_worker import FlightImportThread
from mcm_solarcheck.importers.m3t_original_files_staging import stage_original_m3t_files
import mcm_solarcheck.services.project_pipeline as pipeline
from mcm_solarcheck.services.project_pipeline import ProjectImportCancelled

from test_original_zip_project_bridge import (
    fixture_image, fake_import_in_durable_folder, project,
)
from test_offline_cancellable_import import sample_import


def loose_originals(tmp_path):
    source = tmp_path / "operator-originals"
    source.mkdir()
    thermal = fixture_image((640, 512))
    rgb = fixture_image((4000, 3000))
    t0 = source / "DJI_20250825121642_0128_T.JPG"
    t1 = source / "DJI_20250825121642_0129_T.JPG"
    v0 = source / "DJI_20250825121642_0128_V.JPG"
    t0.write_bytes(thermal)
    t1.write_bytes(thermal)
    v0.write_bytes(rgb)
    return (t0, t1, v0)


def test_unpacked_original_files_persist_with_same_guarded_import(tmp_path, monkeypatch):
    service = project(tmp_path)
    paths = loose_originals(tmp_path)
    originals = tuple(p.read_bytes() for p in paths)
    monkeypatch.setattr(pipeline, "import_m3t_project", fake_import_in_durable_folder)
    events = []
    attempt, imported, _ = service.import_project_original_files_cancellable(
        "PV1", paths,
        on_progress=lambda phase, count: events.append((phase, count)),
    )
    assert attempt.succeeded
    assert imported[1].pairs == 1
    copied = list((tmp_path / "private-m3t-originals").iterdir())
    assert len(copied) == 1
    saved = copied[0]
    for path, original_bytes in zip(paths, originals):
        assert (saved / path.name).read_bytes() == original_bytes
        assert path.read_bytes() == original_bytes
    manifest = json.loads((saved / "m3t-original-provenance.json").read_text())
    assert manifest["input_mode"] == "selected_original_files"
    assert (manifest["matched_pairs"], manifest["staged_thermal"],
            manifest["staged_rgb"], manifest["unpaired_thermal_explicitly_staged"]) == (
                1, 2, 1, 1,
            )
    assert not any(f["human_reviewed"] or f["training_rights_approved"]
                   for f in manifest["files"])
    assert service.import_summary("PV1").image_pairs == 1
    assert service.import_summary("PV2").thermal_frames == 0
    assert any(phase == "Unveränderte Originale sichern" for phase, _ in events)
    with pytest.raises(PermissionError, match="leeres Projekt"):
        service.import_project_original_files_cancellable("PV1", paths)


def test_failure_rolls_back_new_copies_and_keeps_other_project(tmp_path, monkeypatch):
    service = project(tmp_path)
    originals = loose_originals(tmp_path)
    before = tuple(p.read_bytes() for p in originals)
    monkeypatch.setattr(
        pipeline, "import_m3t_project",
        lambda *a, **kw: sample_import(broken_thermal=True),
    )
    attempt, imported, _ = service.import_project_original_files_cancellable(
        "PV1", originals,
    )
    assert not attempt.succeeded
    assert imported is None
    assert tuple(p.read_bytes() for p in originals) == before
    assert not list((tmp_path / "private-m3t-originals").iterdir())
    assert service.import_summary("PV1").rgb_frames == 0
    assert service.import_summary("PV2").rgb_frames == 0


def test_cancel_during_staging_is_safe_and_does_not_decode(tmp_path, monkeypatch):
    service = project(tmp_path)
    originals = loose_originals(tmp_path)
    event = Event()
    def progress(phase, number):
        if phase == "Unveränderte Originale sichern":
            event.set()
    monkeypatch.setattr(
        pipeline, "import_m3t_project",
        lambda *_a, **_k: pytest.fail("decoder must not start after cancellation"),
    )
    with pytest.raises(ProjectImportCancelled):
        service.import_project_original_files_cancellable(
            "PV1", originals, should_cancel=event.is_set, on_progress=progress,
        )
    assert not list((tmp_path / "private-m3t-originals").iterdir())
    assert service.import_summary("PV1").thermal_frames == 0


def test_reject_duplicate_counter_or_corrupt_original_without_creating_copy(tmp_path):
    source_files = loose_originals(tmp_path)
    second = tmp_path / "another-original"
    second.mkdir()
    duplicate = second / source_files[0].name
    duplicate.write_bytes(source_files[0].read_bytes())
    target = tmp_path / "safe-new"
    with pytest.raises(ValueError, match="Duplicated"):
        stage_original_m3t_files([*source_files, duplicate], target)
    assert not target.exists()
    source_files[0].write_bytes(b"not a DJI JPEG")
    with pytest.raises((OSError, ValueError)):
        stage_original_m3t_files(source_files, target)
    assert not target.exists()


def test_selected_files_gui_is_default_and_optional_zip_does_not_fire():
    app = QApplication.instance() or QApplication([])
    calls = []
    page = make_import_page(
        current_project_id="PV1",
        on_import_original_files=lambda paths: calls.append(("files", paths)),
        choose_original_files=lambda: ["C:/images/one_T.JPG", "C:/images/one_V.JPG"],
        on_import_images=lambda folder: calls.append(("folder", folder)),
        choose_directory=lambda: "C:/images",
        on_import_original_zips=lambda *args: calls.append(("zip", args)),
        choose_thermal_zip=lambda: "C:/thermal.zip",
        choose_rgb_zip=lambda: "C:/rgb.zip",
    )
    try:
        files = page.findChild(QPushButton, "import_original_files_button")
        folder = page.findChild(QPushButton, "import_images_button")
        zip_button = page.findChild(QPushButton, "import_original_zips_button")
        assert files.isEnabled() and folder.isEnabled() and zip_button.isEnabled()
        assert "ohne ZIP" in files.text()
        assert "Optional" in zip_button.text()
        files.click()
        folder.click()
        assert calls == [
            ("files", ("C:/images/one_T.JPG", "C:/images/one_V.JPG")),
            ("folder", "C:/images"),
        ]
    finally:
        page.close()
    page = make_import_page(current_project_id=None)
    try:
        assert not page.findChild(QPushButton, "import_original_files_button").isEnabled()
    finally:
        page.close()


def test_qthread_uses_original_files_service_without_zip_or_folder():
    class FakeService:
        def import_project_original_files_cancellable(self, project_id, paths, **kwargs):
            assert project_id == "PV1"
            assert paths == ("T.JPG", "V.JPG")
            assert kwargs["should_cancel"]() is False
            return SimpleNamespace(succeeded=True), None, "state"
        def import_project_images_cancellable(self, *args, **kwargs):
            pytest.fail("folder import must not run for selected files")
        def import_project_original_zips_cancellable(self, *args, **kwargs):
            pytest.fail("ZIP import must not run for selected files")
    application = QApplication.instance() or QApplication([])
    worker = FlightImportThread(
        FakeService(), "PV1", "", original_files=("T.JPG", "V.JPG"),
    )
    results = []
    worker.result_ready.connect(lambda result: results.append(result))
    worker.run()
    assert len(results) == 1 and results[0][0].succeeded
    with pytest.raises(ValueError):
        FlightImportThread(
            FakeService(), "PV1", "", original_files=("T.JPG",),
            original_zips=("a.zip", "b.zip"),
        )
