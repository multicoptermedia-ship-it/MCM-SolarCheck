"""Project-selected RGB diagnostic, real Qt surface, no private data writes."""
from __future__ import annotations

import hashlib
import os
import sqlite3
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import cv2
import numpy as np
import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox, QFileDialog, QLabel, QPushButton

from mcm_solarcheck.domain.models import ImageFrame
from mcm_solarcheck.offline.entrypoint import build_offline_window
from mcm_solarcheck.services.shell_navigation import ShellRoute
from mcm_solarcheck.services.rgb_project_preview_vertical import (
    RGBProjectPreviewCancelled,
    create_project_rgb_preview,
    list_project_rgb_pairs,
)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def project(tmp_path, app):
    window = build_offline_window(tmp_path / "safe-test.sqlite3")
    private = tmp_path / "private-originals"
    private.mkdir()
    output = tmp_path / "new-diagnostic"
    output.mkdir()
    rng = np.random.default_rng(26)
    texture = rng.integers(0, 256, (768, 1024, 3), dtype=np.uint8)
    paths = []
    for n in (136, 137):
        original = private / f"DJI_20250825121642_{n:04d}_V.JPG"
        assert cv2.imwrite(str(original), texture)
        paths.append(original)
    window._project_service.create_project("P1", "Testprojekt")
    window._project_service.create_project("P2", "Andere Anlage")
    window._project_service.database.save_image_frames("P1", tuple(
        ImageFrame(f"RGB{n}", path, width=1024, height=768)
        for n, path in zip((136, 137), paths)
    ))
    window._open_project("P1")
    try:
        yield window, paths, output
    finally:
        if window._project_rgb_preview_thread is not None:
            window._project_rgb_preview_thread.request_cancel()
            window._project_rgb_preview_thread.wait(20000)
            app.processEvents()
        window.close()
        app.processEvents()


def _wait_done(window, app):
    for _ in range(400):
        app.processEvents()
        if window._project_rgb_preview_thread is None:
            return
        QTest.qWait(35)
    pytest.fail("RGB worker did not finish")


def test_project_pairs_are_only_from_selected_read_only_sqlite(project):
    window, paths, target = project
    database = window._project_service.database.path
    assert list_project_rgb_pairs(database, "P1") == (("0136", "0137"),)
    assert list_project_rgb_pairs(database, "P2") == ()
    pairs = window._pages[ShellRoute.PROCESSING].findChild(
        QComboBox, "processing_project_rgb_pair_selector"
    )
    assert pairs.count() == 1
    assert pairs.currentData() == ("0136", "0137")
    assert "MPO" not in pairs.currentText()


def test_real_gui_project_to_original_rgb_to_png_and_visible_dialog(project, monkeypatch, app):
    window, sources, target = project
    before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in sources]
    with sqlite3.connect(window._project_service.database.path) as db:
        old = db.execute("SELECT COUNT(*) FROM pv_modules").fetchone()[0]
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", lambda *args, **kwargs: str(target),
    )
    page = window._pages[ShellRoute.PROCESSING]
    button = page.findChild(QPushButton, "processing_start_project_rgb_preview")
    assert button.isEnabled()
    button.click()
    _wait_done(window, app)
    assert sorted(p.name for p in target.iterdir()) == [
        "rgb-stitch-preview.json", "rgb-stitch-preview.png"
    ]
    dialog = window._project_rgb_preview_dialog
    assert dialog is not None and dialog.isVisible()
    warning = dialog.findChild(QLabel, "project_rgb_preview_warning").text()
    assert "Nichtmetrische" in warning
    assert "Dachflächen" in warning
    status = window._pages[ShellRoute.PROCESSING].findChild(
        QLabel, "processing_project_rgb_preview_status"
    ).text()
    assert "nicht metrisch" in status.lower()
    assert all(
        hashlib.sha256(path.read_bytes()).hexdigest() == digest
        for path, digest in zip(sources, before)
    )
    with sqlite3.connect(window._project_service.database.path) as db:
        assert db.execute("SELECT COUNT(*) FROM pv_modules").fetchone()[0] == old
    dialog.close()


def test_cancelled_service_never_publishes_preview(project):
    window, _, target = project
    with pytest.raises(RGBProjectPreviewCancelled):
        create_project_rgb_preview(
            window._project_service.database.path,
            "P1", "0136", "0137", target, should_cancel=lambda: True,
        )
    assert not list(target.iterdir())

    stopped = {"value": False}
    def callback(done, total, stage):
        if done == 2:
            stopped["value"] = True
    with pytest.raises(RGBProjectPreviewCancelled):
        create_project_rgb_preview(
            window._project_service.database.path,
            "P1", "0136", "0137", target,
            on_progress=callback, should_cancel=lambda: stopped["value"],
        )
    assert not list(target.iterdir())


def test_cancel_running_gui_job_and_switch_project_has_no_stale_dialog(
    project, monkeypatch, app,
):
    import time
    from mcm_solarcheck.gui import project_rgb_preview_worker
    window, _, target = project

    def cooperative(*args, should_cancel, on_progress, **kwargs):
        on_progress(1, 3, "RGB-Merkmale registrieren")
        while not should_cancel():
            time.sleep(0.005)
        raise RGBProjectPreviewCancelled("cancelled")

    monkeypatch.setattr(project_rgb_preview_worker, "create_project_rgb_preview", cooperative)
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", lambda *args, **kwargs: str(target),
    )
    window._pages[ShellRoute.PROCESSING].findChild(
        QPushButton, "processing_start_project_rgb_preview"
    ).click()
    assert window._project_rgb_preview_thread is not None
    page = window._pages[ShellRoute.PROCESSING]
    assert page.findChild(QPushButton, "processing_cancel_project_rgb_preview")
    window._open_project("P2")
    _wait_done(window, app)
    assert window._project_rgb_preview_dialog is None
    assert window._current_project_id == "P2"
    newpage = window._pages[ShellRoute.PROCESSING]
    assert not newpage.findChild(
        QPushButton, "processing_start_project_rgb_preview"
    ).isEnabled()
    assert not list(target.iterdir())
