"""Offscreen preview dialog integration on synthetic private JPEG files."""
from __future__ import annotations

import os
import time
from hashlib import sha256

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
pytest.importorskip("PySide6")
from PIL import Image
from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QPushButton

from mcm_solarcheck.offline.entrypoint import build_offline_window
from mcm_solarcheck.services.shell_commands import ShellCommandId
from mcm_solarcheck.services.shell_navigation import ShellRoute


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def test_visual_rgb_overlay_is_ephemeral_and_keeps_review_closed(qt_app, tmp_path):
    window = build_offline_window(tmp_path / "overlay.sqlite")
    svc = window._project_service
    image = tmp_path / "synthetic-not-customer.jpg"
    Image.new("RGB", (192, 144), (55, 110, 150)).save(image)
    original = image.read_bytes()
    try:
        svc.create_project("P1", "Pilot")
        with svc.database.connect() as sql:
            sql.execute(
                "INSERT INTO image_frames "
                "(project_id,frame_id,source_file,width,height) "
                "VALUES (?,?,?,?,?)",
                ("P1", "R1", str(image), 192, 144),
            )
            sql.execute(
                "INSERT INTO training_samples "
                "(sample_id,project_id,source_frame_id,source_file,"
                "modality,content_sha256,label_status,rights_status) "
                "VALUES (?,?,?,?,?,?,?,?)",
                ("S1", "P1", "R1", str(image), "rgb",
                 sha256(original).hexdigest(), "pending", "private"),
            )
        window._open_project("P1")
        window.show_route(ShellRoute.PROCESSING)
        window.show()
        qt_app.processEvents()
        page = window._pages[ShellRoute.PROCESSING]
        combo = page.findChild(QComboBox, "processing_rgb_overlay_selector")
        button = page.findChild(QPushButton, "processing_preview_rgb_overlay")
        assert combo is not None and combo.count() == 1
        assert button is not None and button.isEnabled()
        button.click()
        deadline = time.monotonic() + 15
        while window._rgb_overlay_thread is not None and time.monotonic() < deadline:
            qt_app.processEvents()
            time.sleep(0.01)
        qt_app.processEvents()
        assert window._rgb_overlay_thread is None
        dialog = window._rgb_overlay_dialog
        assert dialog is not None and dialog.isVisible()
        assert dialog.findChild(QLabel, "rgb_module_overlay_legend") is not None
        assert dialog.findChild(QLabel, "rgb_module_overlay_image").pixmap() is not None
        assert "Keine bestätigten" not in dialog.windowTitle()
        assert "keine Fachfreigabe" in dialog.findChild(
            QLabel, "rgb_module_overlay_warning",
        ).text()
        assert image.read_bytes() == original
        assert not window.action(ShellCommandId.REVIEW).isEnabled()
        assert not window.action(ShellCommandId.REPORT).isEnabled()
        assert not window.action(ShellCommandId.EXPORT).isEnabled()
        with svc.database.connect() as sql:
            for table in ("pv_modules", "offline_processing_runs", "finding_reviews"):
                assert sql.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
        dialog.findChild(QPushButton, "rgb_module_overlay_close").click()
        qt_app.processEvents()
        assert (
            window._rgb_overlay_dialog is None
            or not window._rgb_overlay_dialog.isVisible()
        )
    finally:
        window.close()
        qt_app.processEvents()


def test_project_switch_discards_stale_overlay_result(qt_app, tmp_path):
    window = build_offline_window(tmp_path / "stale.sqlite")
    try:
        window._rgb_overlay_project_id = "P1"
        window._current_project_id = "P2"
        window._rgb_overlay_status = None
        window._rgb_overlay_failed("NEVER SHOW")
        assert window._rgb_overlay_status is None
        window._rgb_overlay_cancelled()
        assert window._rgb_overlay_status is None
    finally:
        window.close()
