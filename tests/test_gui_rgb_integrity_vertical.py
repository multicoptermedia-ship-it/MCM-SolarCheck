"""Vertical Qt action -> shared integrity service -> visible result."""
import cv2
import numpy as np
import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from mcm_solarcheck.gui.import_page import make_import_page
from mcm_solarcheck.gui.flight_rgb_integrity_status import format_rgb_integrity_summary
from mcm_solarcheck.services.flight_rgb_batch_resume import inspect_rgb_batch_resume


def test_integrity_action_runs_shared_service_and_displays_status(tmp_path):
    app = QApplication.instance() or QApplication([])
    sources = tmp_path / "jpeg"
    outputs = tmp_path / "working"
    sources.mkdir()
    outputs.mkdir()
    image = sources / "capture.jpg"
    assert cv2.imwrite(str(image), np.zeros((4, 5, 3), dtype=np.uint8))
    received = []

    def inspect(source, destination):
        result = inspect_rgb_batch_resume([image], destination)
        received.append((source, destination, format_rgb_integrity_summary(result)))

    page = make_import_page(
        current_project_id="P1", on_inspect_rgb_integrity=inspect,
        choose_rgb_integrity_folder=lambda: str(sources),
        choose_rgb_integrity_output=lambda: str(outputs),
        rgb_integrity_status="Noch keine Integritätsprüfung.",
    )
    button = page.findChild(QPushButton, "inspect_rgb_integrity_button")
    assert button is not None and button.isEnabled()
    button.click()
    assert received[0][0:2] == (str(sources), str(outputs))
    assert "Arbeitsdatei fehlt" in received[0][2]
    assert "keine authentische Herkunft" in received[0][2]
    assert page.findChild(QLabel, "rgb_integrity_status") is not None
    assert not list(outputs.iterdir())
    page.close()


def test_integrity_action_requires_project_and_cancellation_is_noop():
    app = QApplication.instance() or QApplication([])
    called = []
    page = make_import_page(on_inspect_rgb_integrity=lambda *args: called.append(args))
    assert not page.findChild(QPushButton, "inspect_rgb_integrity_button").isEnabled()
    page.close()
    page = make_import_page(current_project_id="P1",
                            on_inspect_rgb_integrity=lambda *args: called.append(args),
                            choose_rgb_integrity_folder=lambda: "")
    page.findChild(QPushButton, "inspect_rgb_integrity_button").click()
    assert called == []
    page.close()
