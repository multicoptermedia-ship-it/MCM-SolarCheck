"""Qt cancellation control and bounded incremental scan tests."""
import cv2
import numpy as np
import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QPushButton

from mcm_solarcheck.gui.import_page import make_import_page
from mcm_solarcheck.services.flight_rgb_integrity_scan import (
    IntegrityScanCancelled, scan_rgb_integrity,
)


def test_integrity_cancel_button_invokes_callback():
    app = QApplication.instance() or QApplication([])
    calls = []
    page = make_import_page(current_project_id="P1",
                            on_cancel_rgb_integrity=lambda: calls.append(True))
    button = page.findChild(QPushButton, "cancel_rgb_integrity_button")
    assert button.isEnabled()
    button.click()
    assert calls == [True]
    page.close()


def test_scan_reports_progress_and_stops_before_next_file(tmp_path):
    sources, output = tmp_path / "images", tmp_path / "working"
    sources.mkdir()
    output.mkdir()
    for name in ("a.jpg", "b.jpg"):
        assert cv2.imwrite(str(sources / name), np.zeros((4, 5, 3), dtype=np.uint8))
    progress = []
    with pytest.raises(IntegrityScanCancelled):
        scan_rgb_integrity(sources, output,
                           on_progress=lambda *args: progress.append(args),
                           should_cancel=lambda: bool(progress))
    assert progress == [(1, 2, "missing")]
    assert list(output.iterdir()) == []
