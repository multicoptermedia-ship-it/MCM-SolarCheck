"""Windows-pilot usability and guarded incremental import regressions.

All image fixtures are synthetic; no private images or GPS appear in CI.
"""
from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox, QPushButton

import mcm_solarcheck.services.project_pipeline as pipeline
from mcm_solarcheck.gui.flight_import_worker import FlightImportThread
from mcm_solarcheck.gui.import_page import make_import_page
from mcm_solarcheck.gui.shell import SolarCheckMainWindow
from mcm_solarcheck.gui.theme import APP_STYLE_SHEET
from mcm_solarcheck.gui.workflow_navigation import WorkflowNavigation
from mcm_solarcheck.importers.project import ProjectImportResult
from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.shell_navigation import ShellRoute
from test_offline_cancellable_import import sample_import
from test_original_files_project_bridge import loose_originals
from test_original_zip_project_bridge import project


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def test_navigation_remains_legible_and_explains_unavailable_steps(qt_app):
    navigation = WorkflowNavigation(
        (ShellRoute.PROJECT, ShellRoute.IMPORT), lambda _: None,
    )
    assert navigation.minimumWidth() >= 220
    assert "font-size: 18px" in APP_STYLE_SHEET
    assert "background-color: #39423d" in APP_STYLE_SHEET
    import_button = navigation.button(ShellRoute.IMPORT)
    import_button.setProperty("blocked", True)
    navigation.set_availability(ShellRoute.IMPORT, False)
    status = navigation.findChild(QLabel, "import_navigation_status")
    assert status is not None
    assert "Noch nicht bereit" in status.text()
    assert import_button.isEnabled()
    navigation.set_current_route(ShellRoute.IMPORT)
    assert status.text() == "Aktueller Bereich"


def test_primary_folder_ui_and_optional_append_are_separate(qt_app):
    calls = []
    page = make_import_page(
        current_project_id="internal-opaque-id",
        project_label="SC-0003 · Musterdach",
        import_summary=SimpleNamespace(
            rgb_frames=0, thermal_frames=160, image_pairs=0,
        ),
        on_import_flight_folder=lambda folder: calls.append(("folder", folder)),
        choose_flight_folder=lambda: "F:/DJI-Flug",
        on_import_additional_original_files=lambda paths: calls.append(("add", paths)),
        choose_additional_original_files=lambda: ["F:/DJI-Flug/DJI_20250825121642_0128_V.JPG"],
    )
    try:
        label = page.findChild(QLabel, "import_project_context")
        assert label is not None and "SC-0003" in label.text()
        assert "internal-opaque-id" not in label.text()
        folder = page.findChild(QPushButton, "import_flight_folder_button")
        append = page.findChild(QPushButton, "import_append_original_files_button")
        assert folder.isEnabled() and append.isEnabled()
        folder.click()
        append.click()
        assert [kind for kind, _ in calls] == ["folder", "add"]
        assert calls[0][1] == "F:/DJI-Flug"
        assert calls[1][1][0].endswith("_V.JPG")
    finally:
        page.close()


def test_gui_folder_preview_counts_both_modalities_before_import(qt_app, tmp_path, monkeypatch):
    folder = tmp_path / "flight"
    folder.mkdir()
    (folder / "DJI_20250825121642_0128_T.JPG").write_bytes(b"synthetic")
    (folder / "DJI_20250825121642_0128_V.JPG").write_bytes(b"synthetic")
    (folder / "notes.txt").write_text("not an image")
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP)
    window._project_service = object()
    window._current_project_id = "local-project"
    observed = []
    monkeypatch.setattr(
        QMessageBox, "question",
        lambda _parent, _title, message, *_args: (
            observed.append(message), QMessageBox.StandardButton.Yes
        )[1],
    )
    monkeypatch.setattr(
        window, "_request_original_files_import",
        lambda paths: observed.append(tuple(paths)),
    )
    try:
        window._request_flight_folder_import(str(folder))
        assert "1 Thermalbilder und 1 RGB-Bilder" in observed[0]
        assert len(observed[1]) == 2
        assert all(str(folder) in path for path in observed[1])
    finally:
        window.close()


def _split_importer(folder, **_kwargs):
    """Synthetically imitate a thermal-first, RGB-later flight."""
    source = Path(folder)
    names = {path.name for path in source.iterdir()}
    original = sample_import()
    empty_batch = SimpleNamespace(results=(), failures=())
    thermal = "DJI_20250825121642_0128_T.JPG"
    rgb = "DJI_20250825121642_0128_V.JPG"
    if rgb in names:
        frames = (replace(
            original.rgb_frames[0], source_file=source / rgb,
        ),)
        return ProjectImportResult(frames, empty_batch, ())
    result = original.thermal_batch.results[0]
    converted = SimpleNamespace(
        frame=replace(result.frame, source_file=source / thermal),
        quality=result.quality, findings=result.findings,
    )
    return ProjectImportResult(
        (), SimpleNamespace(results=(converted,), failures=()), (),
    )


def test_explicit_append_preserves_thermal_and_rejects_duplicate(tmp_path, monkeypatch):
    service = project(tmp_path)
    thermal1, thermal2, rgb = loose_originals(tmp_path)
    monkeypatch.setattr(pipeline, "import_m3t_project", _split_importer)
    assert service.import_project_original_files_cancellable(
        "PV1", (thermal1, thermal2),
    )[0].succeeded
    before = service.import_summary("PV1")
    assert (before.rgb_frames, before.thermal_frames) == (0, 1)
    assert service.import_project_original_files_cancellable(
        "PV1", (rgb,), append_only=True,
    )[0].succeeded
    after = service.import_summary("PV1")
    assert (after.rgb_frames, after.thermal_frames, after.findings) == (
        1, 1, before.findings,
    )
    assert service.import_summary("PV2").rgb_frames == 0
    # Existing persisted paths/finding identifiers are immutable.
    with service.database.connect() as db:
        source_before = db.execute(
            "SELECT source_file FROM thermal_frames WHERE project_id='PV1'"
        ).fetchone()[0]
    failed, _, _ = service.import_project_original_files_cancellable(
        "PV1", (rgb,), append_only=True,
    )
    assert not failed.succeeded
    assert "bereits" in failed.error
    assert service.import_summary("PV1") == after
    with service.database.connect() as db:
        assert db.execute(
            "SELECT source_file FROM thermal_frames WHERE project_id='PV1'"
        ).fetchone()[0] == source_before
    assert len(tuple((tmp_path / "private-m3t-originals").iterdir())) == 2


def test_append_fails_closed_after_human_review(tmp_path, monkeypatch):
    service = project(tmp_path)
    thermal1, thermal2, rgb = loose_originals(tmp_path)
    monkeypatch.setattr(pipeline, "import_m3t_project", _split_importer)
    assert service.import_project_original_files_cancellable(
        "PV1", (thermal1, thermal2),
    )[0].succeeded
    with service.database.connect() as db:
        db.execute(
            "INSERT INTO finding_reviews "
            "(project_id,finding_id,status,reviewer,reviewed_at_utc,note) "
            "VALUES (?,?,?,?,?,?)",
            ("PV1", "F-1", "confirmed", "synthetic", "2026-10-23T10:00:00Z", ""),
        )
    failed, _, _ = service.import_project_original_files_cancellable(
        "PV1", (rgb,), append_only=True,
    )
    assert not failed.succeeded
    assert "fachlich" in failed.error
    assert service.import_summary("PV1").rgb_frames == 0
    assert len(tuple((tmp_path / "private-m3t-originals").iterdir())) == 1


def test_append_worker_uses_explicit_additive_service(qt_app):
    class FakeService:
        def import_project_original_files_cancellable(self, project_id, paths, **kwargs):
            assert project_id == "PV1"
            assert paths == ("RGB.JPG",)
            assert kwargs["append_only"] is True
            return SimpleNamespace(succeeded=True), None, "state"
    worker = FlightImportThread(
        FakeService(), "PV1", "", original_files=("RGB.JPG",),
        append_original_files=True,
    )
    recorded = []
    worker.result_ready.connect(lambda payload: recorded.append(payload))
    worker.run()
    assert len(recorded) == 1 and recorded[0][0].succeeded
